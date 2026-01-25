
import sys
sys.path.insert(0, ".")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, log_level="info")
