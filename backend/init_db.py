from pathlib import Path

from app.models import Database 
from app.models import WeekModel, EnergyWeeklyModel, WeatherWeeklyModel, HolidayModel
from app.models import UserModel, RoleModel
from app.models import WardModel, WardInfraModel
from app.models import ModelRunModel, PredictionModel
from app.models import ScenarioModel


BASE_DIR = Path(__file__).resolve().parent # -> backend folder

db_path = BASE_DIR / "energy_dss.db"

print(f"Initializing database at: {db_path}")

class InitDataBase:
    @staticmethod
    def init_db():
        db = Database(db_path)

        try:
            db.connect()
            db.execute("PRAGMA foreign_keys = ON")
            
        
            # Transaction (critical)
            with db.transaction():
                # 1. role + user
                RoleModel.create_table(db)
                UserModel.create_table(db)
                
                # 2. time
                WeekModel.create_table(db)
                
                # 3 core data
                EnergyWeeklyModel.create_table(db)
                WeatherWeeklyModel.create_table(db)
                HolidayModel.create_table(db)
                
                # 4. ward
                WardModel.create_table(db)
                WardInfraModel.create_table(db)
                
                # 5. model + prediction
                ModelRunModel.create_table(db)
                PredictionModel.create_table(db)
                
                # 6. scenario
                ScenarioModel.create_table(db)
                
                # == SEEDING (optional) ==
                RoleModel.seed(db)
                UserModel.seed_admin(db, role_id=1) # admin role_id = 1
                dev_role = RoleModel.get_by_name(db, "dev")
                if dev_role:
                    UserModel.seed_dev(db, role_id=dev_role["id"])
            
        except Exception as e:
            db.close()
            raise RuntimeError(f"DB init failed: {e}")
        
        return db
    
    @staticmethod
    def get_db():
        db = Database(db_path)
        db.connect()
        db.execute("PRAGMA foreign_keys = ON")
        return db
        
    @staticmethod
    def close_db(db):
        if db:
            db.close()
        
