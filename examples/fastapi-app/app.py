# examples/fastapi-app/app.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
import torch.nn as nn
import numpy as np
import asyncio
import time
import os
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import psutil
import GPUtil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Model Inference API",
    description="Production-ready ML model deployment with GPU support",
    version="1.0.0"
)

# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=4)

# Global model variable
model = None
device = None

# Request/Response models
class PredictionRequest(BaseModel):
    input_data: List[float]
    batch_size: Optional[int] = 1
    return_probabilities: Optional[bool] = False

class PredictionResponse(BaseModel):
    prediction: List[float]
    probabilities: Optional[List[List[float]]] = None
    processing_time: float
    model_version: str = "1.0.0"

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_used: Optional[float] = None
    gpu_memory_total: Optional[float] = None
    cpu_percent: float
    memory_percent: float
    model_loaded: bool
    uptime_seconds: float

# Simple example model (replace with your actual model)
class SimpleModel(nn.Module):
    def __init__(self, input_dim=10, hidden_dim=128, output_dim=5):
        super(SimpleModel, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        return self.layers(x)

# Startup time for uptime calculation
startup_time = time.time()

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    global model, device
    
    logger.info("Starting ML Model Service...")
    
    # Detect device
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        logger.info("No GPU detected, using CPU")
    
    # Load model
    try:
        model_path = os.environ.get("MODEL_PATH", "model.pth")
        
        # Initialize model (replace with your model loading logic)
        model = SimpleModel()
        
        # Load weights if file exists
        if os.path.exists(model_path):
            logger.info(f"Loading model from {model_path}")
            model.load_state_dict(torch.load(model_path, map_location=device))
        else:
            logger.warning(f"Model file not found at {model_path}, using random weights")
        
        model = model.to(device)
        model.eval()
        
        logger.info("Model loaded successfully")
        
        # Warmup inference
        warmup_input = torch.randn(1, 10).to(device)
        with torch.no_grad():
            _ = model(warmup_input)
        logger.info("Model warmup complete")
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "ML Model Inference API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with system metrics"""
    try:
        # GPU metrics
        gpu_available = torch.cuda.is_available()
        gpu_name = None
        gpu_memory_used = None
        gpu_memory_total = None
        
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory_used = torch.cuda.memory_allocated(0) / 1024**3  # Convert to GB
            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            # Try to get GPU utilization
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_memory_used = gpus[0].memoryUsed / 1024  # Convert to GB
                    gpu_memory_total = gpus[0].memoryTotal / 1024
            except:
                pass
        
        # CPU and memory metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # Uptime
        uptime = time.time() - startup_time
        
        return HealthResponse(
            status="healthy",
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            gpu_memory_used=round(gpu_memory_used, 2) if gpu_memory_used else None,
            gpu_memory_total=round(gpu_memory_total, 2) if gpu_memory_total else None,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            model_loaded=model is not None,
            uptime_seconds=round(uptime, 2)
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Main prediction endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Validate input
        if len(request.input_data) == 0:
            raise HTTPException(status_code=400, detail="Input data cannot be empty")
        
        # Prepare input tensor
        input_array = np.array(request.input_data).reshape(request.batch_size, -1)
        input_tensor = torch.FloatTensor(input_array).to(device)
        
        # Run inference
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            executor,
            run_inference,
            model,
            input_tensor,
            request.return_probabilities
        )
        
        # Prepare response
        processing_time = time.time() - start_time
        
        response = PredictionResponse(
            prediction=output["predictions"],
            processing_time=processing_time
        )
        
        if request.return_probabilities:
            response.probabilities = output["probabilities"]
        
        # Log prediction in background
        background_tasks.add_task(
            log_prediction,
            request_size=len(request.input_data),
            processing_time=processing_time
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

def run_inference(model: nn.Module, input_tensor: torch.Tensor, return_probs: bool) -> Dict[str, Any]:
    """Run model inference"""
    with torch.no_grad():
        output = model(input_tensor)
        
        # Apply softmax for probabilities
        probabilities = torch.softmax(output, dim=1)
        predictions = torch.argmax(probabilities, dim=1)
        
        result = {
            "predictions": predictions.cpu().tolist()
        }
        
        if return_probs:
            result["probabilities"] = probabilities.cpu().tolist()
        
        return result

async def log_prediction(request_size: int, processing_time: float):
    """Background task to log predictions"""
    logger.info(f"Prediction completed - Size: {request_size}, Time: {processing_time:.3f}s")

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    metrics_data = []
    
    # Model metrics
    metrics_data.append(f"model_loaded {{version=\"1.0.0\"}} {1 if model is not None else 0}")
    
    # GPU metrics
    if torch.cuda.is_available():
        gpu_memory_used = torch.cuda.memory_allocated(0) / 1024**3
        gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        metrics_data.append(f"gpu_memory_used_gb {gpu_memory_used:.2f}")
        metrics_data.append(f"gpu_memory_total_gb {gpu_memory_total:.2f}")
        metrics_data.append(f"gpu_available 1")
    else:
        metrics_data.append(f"gpu_available 0")
    
    # System metrics
    metrics_data.append(f"cpu_usage_percent {psutil.cpu_percent()}")
    metrics_data.append(f"memory_usage_percent {psutil.virtual_memory().percent}")
    metrics_data.append(f"uptime_seconds {time.time() - startup_time:.2f}")
    
    return "\n".join(metrics_data)

@app.get("/model/info")
async def model_info():
    """Get model information"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    return {
        "model_type": model.__class__.__name__,
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "device": str(device),
        "model_version": "1.0.0",
        "framework": f"PyTorch {torch.__version__}"
    }

@app.post("/batch_predict")
async def batch_predict(requests: List[PredictionRequest]):
    """Batch prediction endpoint for multiple inputs"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    results = []
    
    try:
        # Combine all inputs into a single batch
        all_inputs = []
        for req in requests:
            input_array = np.array(req.input_data).reshape(req.batch_size, -1)
            all_inputs.append(input_array)
        
        # Stack inputs
        batch_input = np.vstack(all_inputs)
        input_tensor = torch.FloatTensor(batch_input).to(device)
        
        # Run batch inference
        with torch.no_grad():
            output = model(input_tensor)
            probabilities = torch.softmax(output, dim=1)
            predictions = torch.argmax(probabilities, dim=1)
        
        # Split results back
        idx = 0
        for req in requests:
            batch_size = req.batch_size
            pred_slice = predictions[idx:idx+batch_size].cpu().tolist()
            
            result = {
                "prediction": pred_slice,
                "processing_time": time.time() - start_time
            }
            
            if req.return_probabilities:
                prob_slice = probabilities[idx:idx+batch_size].cpu().tolist()
                result["probabilities"] = prob_slice
            
            results.append(result)
            idx += batch_size
        
        return {"results": results, "total_processing_time": time.time() - start_time}
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
