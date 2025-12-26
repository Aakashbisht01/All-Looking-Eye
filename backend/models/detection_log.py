"""
Detection Log model for MongoDB
Stores event logs only (no video file paths)
"""
from datetime import datetime
from bson import ObjectId

class DetectionLog:
    """Detection log document schema for MongoDB"""
    
    collection_name = 'detection_logs'
    
    @staticmethod
    def create_log(db, email, source_type, anomaly_type, confidence_score, 
                   email_sent=False, metadata=None):
        """Create a new detection log entry (event only, no video path)"""
        log_doc = {
            'email': email.lower().strip() if email else '',
            'source_type': source_type,  # 'upload', 'camera', 'cctv'
            'timestamp': datetime.utcnow(),
            'anomaly_type': anomaly_type,  # 'violence', 'audio', 'combined', 'normal'
            'confidence_score': confidence_score,
            'email_sent': email_sent,
            'metadata': metadata or {}
        }
        result = db[DetectionLog.collection_name].insert_one(log_doc)
        log_doc['_id'] = result.inserted_id
        return log_doc
    
    @staticmethod
    def find_by_email(db, email, limit=50, skip=0):
        """Find detection logs for an email"""
        return list(db[DetectionLog.collection_name].find(
            {'email': email.lower().strip() if email else ''}
        ).sort('timestamp', -1).skip(skip).limit(limit))
    
    @staticmethod
    def find_anomalies_by_email(db, email, limit=50):
        """Find only anomaly detections for an email"""
        return list(db[DetectionLog.collection_name].find({
            'email': email.lower().strip() if email else '',
            'anomaly_type': {'$ne': 'normal'}
        }).sort('timestamp', -1).limit(limit))
    
    @staticmethod
    def update_email_status(db, log_id, email_sent=True):
        """Update email sent status"""
        if isinstance(log_id, str):
            log_id = ObjectId(log_id)
        return db[DetectionLog.collection_name].update_one(
            {'_id': log_id},
            {'$set': {'email_sent': email_sent}}
        )
    
    @staticmethod
    def get_stats(db, email):
        """Get detection statistics for an email"""
        pipeline = [
            {'$match': {'email': email.lower().strip() if email else ''}},
            {'$group': {
                '_id': '$anomaly_type',
                'count': {'$sum': 1},
                'avg_confidence': {'$avg': '$confidence_score'}
            }}
        ]
        return list(db[DetectionLog.collection_name].aggregate(pipeline))
    
    @staticmethod
    def ensure_indexes(db):
        """Create necessary indexes"""
        db[DetectionLog.collection_name].create_index('email')
        db[DetectionLog.collection_name].create_index('timestamp')
        db[DetectionLog.collection_name].create_index([('email', 1), ('timestamp', -1)])
