from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 定義資料表模型
class UserInfo(db.Model):
    __tablename__ = 'user_info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class Statistics(db.Model):
    __tablename__ = 'statistics'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

class DataRecords(db.Model):
    __tablename__ = 'data_records'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statistic_id = db.Column(db.Integer, db.ForeignKey('statistics.id', ondelete='CASCADE'), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'statistic_id': self.statistic_id,
            'value': self.value,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')  # 格式化時間
        }

def add_user(name, password):
    new_user = UserInfo(name=name, password=password)
    db.session.add(new_user)
    db.session.commit()

def get_user(name):
    user = UserInfo.query.filter_by(name=name).first()
    return user

def verify_user(name, password):
    user = UserInfo.query.filter_by(name=name, password=password).first()
    return user

def delete_user(name):
    user = UserInfo.query.filter_by(name=name).first()
    if user:
        db.session.delete(user)
        db.session.commit()
