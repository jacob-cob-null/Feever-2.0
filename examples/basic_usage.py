import logging
import os
import sys

# Ensure src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from src.medical_services_digitizer import MedicalServicesDigitizer

logging.basicConfig(level=logging.INFO)

def main():
    os.makedirs("./data", exist_ok=True)
    dummy_image = "./data/dummy_test.jpg"
    if not os.path.exists(dummy_image):
        from PIL import Image
        img = Image.new('RGB', (200, 100), color = (73, 109, 137))
        img.save(dummy_image)
        logging.info(f"Created basic dummy image at {dummy_image}")
        
    digitizer = MedicalServicesDigitizer(db_url="sqlite:///./data/medical_services.db")
    
    print("Testing digitizer...")
    result = digitizer.process_image(dummy_image)
    
    print("\nExtracted services:")
    print(json.dumps(result["services"], indent=2))
    
    db_facility = "MOCK Hospital"
    if result["services"]:
        db_facility = result["services"][0].get("facility", "MOCK Hospital")
        
    print(f"\nQuerying Database for '{db_facility}':")
    query_results = digitizer.query({"facility": db_facility})
    # Convert datetime to string for json serialization
    for r in query_results:
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
    print(json.dumps(query_results, indent=2))

if __name__ == "__main__":
    main()
