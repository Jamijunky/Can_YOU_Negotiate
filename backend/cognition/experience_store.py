import sqlite3
import json
import uuid
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class OutcomeSignal(BaseModel):
    session_id: str
    goal_achieved: bool
    negotiator_complied: bool
    promises_broken: int = 0
    promises_kept: int = 0
    human_realism_rating: Optional[float] = None  # 0.0 to 1.0
    final_trust: float = 0.0

class ExperienceStore:
    def __init__(self, db_path: str = "experience.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Turn Experiences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS turn_experience (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    human_model_id TEXT,
                    timestamp REAL,
                    input_transcript TEXT,
                    state_before TEXT,
                    appraisal TEXT,
                    behavioral_decision TEXT,
                    generated_speech TEXT,
                    expression TEXT,
                    latencies TEXT
                )
            ''')
            # Outcomes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_outcomes (
                    session_id TEXT PRIMARY KEY,
                    human_model_id TEXT,
                    timestamp REAL,
                    goal_achieved BOOLEAN,
                    negotiator_complied BOOLEAN,
                    promises_broken INTEGER,
                    promises_kept INTEGER,
                    human_realism_rating REAL,
                    final_trust REAL
                )
            ''')
            # Calibration Versions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calibration_versions (
                    version_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    source_experience_count INTEGER,
                    parameter_changes TEXT
                )
            ''')
            conn.commit()
            
    def store_turn_trace(self, session_id: str, human_model_id: str, trace_dict: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO turn_experience (
                    turn_id, session_id, human_model_id, timestamp, 
                    input_transcript, state_before, appraisal, 
                    behavioral_decision, generated_speech, expression, latencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trace_dict.get("turn_id", str(uuid.uuid4())),
                session_id,
                human_model_id,
                trace_dict.get("timestamp", time.time()),
                trace_dict.get("input_transcript", ""),
                json.dumps(trace_dict.get("state_before", {})),
                json.dumps(trace_dict.get("appraisal", {})),
                json.dumps(trace_dict.get("behavioral_decision", {})),
                trace_dict.get("generated_speech", ""),
                json.dumps(trace_dict.get("expression", {})),
                json.dumps(trace_dict.get("latencies_ms", {}))
            ))
            conn.commit()

    def store_outcome(self, human_model_id: str, outcome: OutcomeSignal):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO session_outcomes (
                    session_id, human_model_id, timestamp, goal_achieved,
                    negotiator_complied, promises_broken, promises_kept,
                    human_realism_rating, final_trust
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                outcome.session_id,
                human_model_id,
                time.time(),
                outcome.goal_achieved,
                outcome.negotiator_complied,
                outcome.promises_broken,
                outcome.promises_kept,
                outcome.human_realism_rating,
                outcome.final_trust
            ))
            conn.commit()
            
    def get_all_outcomes(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_outcomes")
            return [dict(r) for r in cursor.fetchall()]
            
    def store_calibration(self, version_id: str, count: int, changes: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO calibration_versions (
                    version_id, timestamp, source_experience_count, parameter_changes
                ) VALUES (?, ?, ?, ?)
            ''', (
                version_id,
                time.time(),
                count,
                json.dumps(changes)
            ))
            conn.commit()
