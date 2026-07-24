from fastapi import FastAPI


app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}



def main():
    print("Hello from backend!")



if __name__ == "__main__":
    main()
