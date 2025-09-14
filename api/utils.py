# api/utils.py
import json
from bson import ObjectId, Decimal128
from datetime import date, datetime

class MongoDBJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, Decimal128):
            return float(str(obj))  # Convert Decimal128 to float
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Use this encoder in your views