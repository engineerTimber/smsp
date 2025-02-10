import json
from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from db import db, UserInfo, Statistics, DataRecords, add_user, get_user, delete_user, verify_user
from flask_cors import CORS
import pandas as pd
import io

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:ybjdb@127.0.0.1:3307/smsp_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# 路由
@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.get_json()  # 獲取前端傳來的 JSON 資料
    name = data.get('name')
    password = data.get('password')
    mode = data.get('mode')  # 'login' 或 'register'

    if not name or not password or not mode:
        return jsonify({"error": "Missing required fields", "message": "你有欄為沒填喔!"}), 400    
    
    existing_user = get_user(name)

    if mode == 'login':
        # 處理登入邏輯，例如：檢查用戶名和密碼是否正確
        if not existing_user:
            return jsonify({"error": "User not found", 
                            "message": "查無此人:(，請先註冊帳號"}), 404
        if not verify_user(name, password):
            return jsonify({"error": "Invalid password",
                            "message": "密碼錯誤"}), 400
        return jsonify({"message": f"登入成功，歡迎 {name}!", "user_id": existing_user.id}), 200

    elif mode == 'register':
        if existing_user:
            return jsonify({"error": "Username already exists. Please choose a different one.",
                            "message": "這個名字被用過惹，換一個吧!"}), 400
        else:
            add_user(name, password)
        # 處理註冊邏輯，例如：創建新用戶
        return jsonify({"message": f"註冊成功，歡迎 {name}! 密碼:{password}，請重新登入！"}), 201
    
    return jsonify({"error": "無效的模式"}), 400

@app.route('/api/users/<int:user_id>/delete', methods=['DELETE'])
def delete_user(user_id):
    user = UserInfo.query.get(user_id)
    if not user:
        return jsonify({"error": "用戶不存在"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "用戶已刪除"}), 200

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    user_id = request.args.get('user_id')  # 透過 Query String 獲取 user_id

    if not user_id:
        return jsonify({'error': '缺少 user_id'}), 400

    statistics = Statistics.query.filter_by(user_id=user_id).all()

    statistics_data = [{'id': stat.id, 'title': stat.title} for stat in statistics]

    return jsonify(statistics_data)

@app.route('/api/statistics', methods=['POST'])
def add_statistic():
    data = request.json
    user_id = data.get('user_id')
    title = data.get('title')

    if not user_id or not title:
        return jsonify({'error': '缺少 user_id 或 title'}), 400

    # 確保該 user 存在
    user = UserInfo.query.get(user_id)
    if not user:
        return jsonify({'error': '用戶不存在'}), 404

    # 建立新的統計項目
    new_statistic = Statistics(user_id=user_id, title=title)
    db.session.add(new_statistic)
    db.session.commit()

    return jsonify({'message': '統計項目已新增', 'statistic_id': new_statistic.id}), 201

@app.route('/api/statistics/<int:stat_id>/title', methods=['PUT'])
def update_statistic_title(stat_id):
    data = request.json
    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({'error': '統計項目不存在'}), 404

    statistic.title = data.get('titleNow', statistic.title)
    db.session.commit()
    return jsonify({'message': '標題已更新'})

@app.route('/api/statistics/<int:stat_id>/note', methods=['GET'])
def get_note(stat_id):
    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({"error": "統計項目不存在"}), 404

    return jsonify({"note": statistic.note})

@app.route('/api/statistics/<int:stat_id>/note', methods=['PUT'])
def update_note(stat_id):
    data = request.json
    new_note = data.get("note")

    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({"error": "統計項目不存在"}), 404

    statistic.note = new_note
    db.session.commit()

    return jsonify({"message": "備註更新成功", "note": statistic.note})

@app.route('/api/statistics/<int:stat_id>/delete', methods=['DELETE'])
def delete_statistic(stat_id):
    # 查詢該統計項目是否存在
    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({"error": "統計項目不存在"}), 404

    # 刪除統計項目
    db.session.delete(statistic)
    db.session.commit()

    return jsonify({"message": "統計項目已刪除"}), 200

@app.route('/api/statistics/<int:stat_id>/data', methods=['POST'])
def add_data(stat_id):
    # 接收用戶資料
    data = request.json
    value = data.get('value')

    if not value:
        return jsonify({'error': '缺少資料值'}), 400

    # 確保該統計項目存在
    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({'error': '統計項目不存在'}), 404

    # 創建新的資料記錄
    new_data = DataRecords(statistic_id=stat_id, value=value)
    db.session.add(new_data)
    db.session.commit()

    return jsonify({'message': '資料已新增', 'data': new_data.to_dict()}), 201

@app.route('/api/statistics/<int:stat_id>/data', methods=['GET'])
def get_data(stat_id):
    # 查詢該統計項目的所有資料
    data_records = DataRecords.query.filter_by(statistic_id=stat_id).order_by(DataRecords.created_at).all() # 可調整加入時間排序
    data_list = [record.to_dict() for record in data_records]

    return jsonify({'data': data_list}), 200

@app.route('/api/data/<int:data_id>/edit', methods=['PUT'])
def update_data_record(data_id):
    data = request.json
    record = DataRecords.query.get(data_id)
    if not record:
        return jsonify({'error': '數據不存在'}), 404

    record.value = data.get('value', record.value)
    db.session.commit()
    return jsonify({'message': '數據已更新'})

@app.route('/api/statistics/data/<int:data_id>/delete', methods=['DELETE'])
def delete_data_record(data_id):
    record = DataRecords.query.get(data_id)
    if not record:
        return jsonify({"error": "數據不存在"}), 404

    db.session.delete(record)
    db.session.commit()
    
    return jsonify({"message": "數據已刪除"}), 200

# 匯出統計數據成xlsx檔案
@app.route('/api/statistics/<int:stat_id>/export-as-xlsx', methods=['GET'])
def export_statistics(stat_id):
    # 查詢該統計項目的資料
    statistic = Statistics.query.get(stat_id)
    if not statistic:
        return jsonify({'error': '統計項目不存在'}), 404

    # 查詢該統計項目下的所有資料
    data_records = DataRecords.query.filter_by(statistic_id=stat_id).order_by(DataRecords.created_at).all() # 可調整加入時間排序

    # 轉換為 DataFrame
    data = {
        "編號": [i for i in range(1, len(data_records)+1)],
        "數據": [record.value for record in data_records],
        "加入時間": [record.created_at.strftime('%Y-%m-%d %H:%M:%S') for record in data_records],
    }
    df = pd.DataFrame(data)

    # 建立記憶體內的 Excel 檔案（不存到硬碟）
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    output.seek(0)

    # 直接回傳 Excel 檔案給前端
    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=statistics_{stat_id}.xlsx"}
    )


if __name__ == '__main__':
    # 初始化資料庫
    with app.app_context():
        db.create_all()
    app.run()
    