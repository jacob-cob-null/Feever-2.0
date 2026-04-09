from typing import Dict, Tuple, List, Callable

class Validators:
    def __init__(self):
        self.rules: List[Callable[[Dict], Tuple[bool, str]]] = [
            self._validate_required_fields,
            self._validate_price,
            self._validate_service_name
        ]
        
    def _validate_required_fields(self, data: Dict) -> Tuple[bool, str]:
        required = ["service_name", "price", "facility"]
        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, ""
        
    def _validate_price(self, data: Dict) -> Tuple[bool, str]:
        price = data.get("price")
        try:
            p = float(price)
            if not (0.01 <= p <= 10000000.0):
                return False, f"Price {p} out of valid range."
            data["price"] = p
        except (ValueError, TypeError):
            return False, "Price is not a valid number."
        return True, ""
        
    def _validate_service_name(self, data: Dict) -> Tuple[bool, str]:
        name = data.get("service_name", "")
        if not (3 <= len(str(name)) <= 200):
            return False, "Service name length must be between 3 and 200 characters."
        return True, ""

    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        errors = []
        for rule in self.rules:
            valid, msg = rule(data)
            if not valid:
                errors.append(msg)
        return len(errors) == 0, errors
