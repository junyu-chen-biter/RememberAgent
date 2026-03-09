import sqlite3
import os
import pandas as pd

DB_NAME = "knowledge_agent.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Create subjects table
    # subjects: id (PK), name, difficulty (float), credits (float), ddl (date string)
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            difficulty REAL,
            credits REAL,
            ddl TEXT
        )
    ''')
    
    # Create cards table
    # cards: id (PK), subject_id (FK), question, answer, created_at, last_reviewed_at, review_count, mastery_level (0-5)
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            question TEXT,
            answer TEXT,
            created_at TEXT,
            last_reviewed_at TEXT,
            review_count INTEGER DEFAULT 0,
            mastery_level INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_subject(name, difficulty, credits, ddl):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO subjects (name, difficulty, credits, ddl) VALUES (?, ?, ?, ?)', 
              (name, difficulty, credits, ddl))
    conn.commit()
    conn.close()

def get_all_subjects():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM subjects", conn)
    conn.close()
    return df

def add_cards(subject_id, qa_list):
    conn = get_connection()
    c = conn.cursor()
    
    from datetime import datetime
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data_to_insert = [
        (subject_id, item['q'], item['a'], created_at, created_at)
        for item in qa_list
    ]
    
    c.executemany('''
        INSERT INTO cards (subject_id, question, answer, created_at, last_reviewed_at, review_count, mastery_level)
        VALUES (?, ?, ?, ?, ?, 0, 0)
    ''', data_to_insert)
    
    conn.commit()
    conn.close()

def get_card_for_review():
    conn = get_connection()
    c = conn.cursor()
    # Randomly select one card where mastery_level < 5
    c.execute('SELECT * FROM cards WHERE mastery_level < 5 ORDER BY RANDOM() LIMIT 1')
    card = c.fetchone()
    conn.close()
    
    if card:
        # Return as a dictionary for easier access
        # cards: id, subject_id, question, answer, created_at, last_reviewed_at, review_count, mastery_level
        return {
            "id": card[0],
            "subject_id": card[1],
            "question": card[2],
            "answer": card[3],
            "created_at": card[4],
            "last_reviewed_at": card[5],
            "review_count": card[6],
            "mastery_level": card[7]
        }
    return None

def get_recommended_cards():
    conn = get_connection()
    c = conn.cursor()
    
    # Fetch all cards with their subject details
    query = '''
        SELECT 
            c.id, c.subject_id, c.question, c.answer, c.created_at, c.last_reviewed_at, c.review_count, c.mastery_level,
            s.ddl, s.credits, s.difficulty
        FROM cards c
        JOIN subjects s ON c.subject_id = s.id
        WHERE c.mastery_level < 5
    '''
    c.execute(query)
    cards = c.fetchall()
    conn.close()
    
    if not cards:
        return None
        
    from datetime import datetime
    
    weighted_cards = []
    current_time = datetime.now()
    
    # Weights (customizable)
    W_URGENCY = 100.0  # Increased weight to make DDL very significant
    W_IMPORTANCE = 5.0
    W_FORGET = 2.0
    W_MASTERY = 3.0
    
    for card in cards:
        card_id, subject_id, question, answer, created_at, last_reviewed_at, review_count, mastery_level, ddl_str, credits, difficulty = card
        
        # 1. Urgency: 1 / (days_left + 1)
        urgency_score = 0
        days_left = 999
        try:
            if ddl_str:
                ddl_date = datetime.strptime(ddl_str, "%Y-%m-%d")
                days_left = (ddl_date - current_time).days
                if days_left < 0: 
                    urgency_score = 2.0 # Overdue is extremely urgent
                else:
                    urgency_score = 1.0 / (days_left + 1)
        except Exception as e:
            # print(f"Date parsing error: {e}")
            pass
            
        # 2. Importance: credits * difficulty
        importance_score = (credits if credits else 1.0) * (difficulty if difficulty else 1.0)
        
        # 3. Forgetfulness: days since last review
        days_since_review = 0
        try:
            if last_reviewed_at:
                last_review_date = datetime.strptime(last_reviewed_at, "%Y-%m-%d %H:%M:%S")
                days_since_review = (current_time - last_review_date).days
            else:
                days_since_review = 100 # Never reviewed
        except:
            days_since_review = 100
            
        forget_score = days_since_review
        
        # 4. Mastery gap: 5 - mastery_level
        mastery_gap = 5 - (mastery_level if mastery_level else 0)
        
        # Final Priority Score
        priority_score = (urgency_score * W_URGENCY) + \
                         (importance_score * W_IMPORTANCE) + \
                         (forget_score * W_FORGET) + \
                         (mastery_gap * W_MASTERY)
                         
        # Determine main reason for recommendation
        reasons = []
        if urgency_score >= 0.1: # Within 10 days roughly
            if days_left < 0: reasons.append("已逾期")
            elif days_left < 3: reasons.append(f"DDL 仅剩 {days_left} 天")
            else: reasons.append("DDL 临近")
            
        if days_since_review > 7: reasons.append("很久没复习")
        if mastery_level is not None and mastery_level < 2: reasons.append("掌握度低")
        if importance_score > 10: reasons.append("重点学科")
        
        reason_text = " + ".join(reasons) if reasons else "综合推荐"
        
        weighted_cards.append({
            "id": card_id,
            "subject_id": subject_id,
            "question": question,
            "answer": answer,
            "created_at": created_at,
            "last_reviewed_at": last_reviewed_at,
            "review_count": review_count,
            "mastery_level": mastery_level,
            "priority_score": priority_score,
            "reason": reason_text
        })
    
    # Sort by priority_score descending
    weighted_cards.sort(key=lambda x: x['priority_score'], reverse=True)
    
    if weighted_cards:
        return weighted_cards[0]
    return None

def get_top_priority_cards(limit=5):
    # Reuses the logic from get_recommended_cards but returns top N
    conn = get_connection()
    c = conn.cursor()
    
    query = '''
        SELECT 
            c.id, c.subject_id, c.question, c.answer, c.created_at, c.last_reviewed_at, c.review_count, c.mastery_level,
            s.ddl, s.credits, s.difficulty, s.name
        FROM cards c
        JOIN subjects s ON c.subject_id = s.id
        WHERE c.mastery_level < 5
    '''
    c.execute(query)
    cards = c.fetchall()
    conn.close()
    
    if not cards:
        return []
        
    from datetime import datetime
    
    weighted_cards = []
    current_time = datetime.now()
    
    W_URGENCY = 100.0
    W_IMPORTANCE = 5.0
    W_FORGET = 2.0
    W_MASTERY = 3.0
    
    for card in cards:
        card_id, subject_id, question, answer, created_at, last_reviewed_at, review_count, mastery_level, ddl_str, credits, difficulty, subject_name = card
        
        # Urgency
        urgency_score = 0
        days_left = 999
        try:
            if ddl_str:
                ddl_date = datetime.strptime(ddl_str, "%Y-%m-%d")
                days_left = (ddl_date - current_time).days
                if days_left < 0: 
                    urgency_score = 2.0 
                else:
                    urgency_score = 1.0 / (days_left + 1)
        except:
            pass
            
        # Importance
        importance_score = (credits if credits else 1.0) * (difficulty if difficulty else 1.0)
        
        # Forgetfulness
        days_since_review = 0
        try:
            if last_reviewed_at:
                last_review_date = datetime.strptime(last_reviewed_at, "%Y-%m-%d %H:%M:%S")
                days_since_review = (current_time - last_review_date).days
            else:
                days_since_review = 100
        except:
            days_since_review = 100
            
        forget_score = days_since_review
        
        # Mastery
        mastery_gap = 5 - (mastery_level if mastery_level else 0)
        
        # Priority Score
        priority_score = (urgency_score * W_URGENCY) + \
                         (importance_score * W_IMPORTANCE) + \
                         (forget_score * W_FORGET) + \
                         (mastery_gap * W_MASTERY)
                         
        weighted_cards.append({
            "question": question,
            "subject_name": subject_name,
            "priority_score": priority_score
        })
    
    weighted_cards.sort(key=lambda x: x['priority_score'], reverse=True)
    return weighted_cards[:limit]

def get_dashboard_stats():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Total cards
    c.execute("SELECT COUNT(*) FROM cards")
    total_cards = c.fetchone()[0]
    
    # 2. Today's reviews
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM cards WHERE date(last_reviewed_at) = ?", (today_str,))
    today_reviews = c.fetchone()[0] # This counts unique cards reviewed today, if we want total attempts we need a separate log table, but this is fine for now
    
    # Actually, the requirement says "今日已复习次数". 
    # Since we update last_reviewed_at every time, this query gets cards reviewed today.
    # If a user reviews the same card twice today, it counts as 1 here.
    # To count exact attempts we'd need a history table. 
    # But for simple MVP, let's assume this means "Number of cards reviewed today".
    
    # 3. Overall Mastery (Average mastery_level)
    c.execute("SELECT AVG(mastery_level) FROM cards")
    avg_mastery = c.fetchone()[0]
    avg_mastery = round(avg_mastery, 2) if avg_mastery else 0.0
    
    # 4. Progress per subject
    # Completion rate = (sum of mastery_level) / (count * 5) * 100 ? 
    # Or just average mastery / 5?
    # Let's use: Average Mastery % per subject
    
    df = pd.read_sql_query('''
        SELECT s.name, AVG(c.mastery_level) as avg_mastery, COUNT(c.id) as card_count
        FROM subjects s
        LEFT JOIN cards c ON s.id = c.subject_id
        GROUP BY s.id
    ''', conn)
    
    # Fill NaN
    df['avg_mastery'] = df['avg_mastery'].fillna(0)
    df['progress'] = (df['avg_mastery'] / 5.0)
    
    conn.close()
    
    return {
        "total_cards": total_cards,
        "today_reviews": today_reviews,
        "avg_mastery": avg_mastery,
        "subject_progress": df
    }

def update_card_progress(card_id, new_mastery_level):
    """
    根据用户自评结果更新某张卡片的掌握度和复习记录。
    new_mastery_level 约定取值：
        2 -> 已经烂熟于心（大幅降低推荐频率）
        1 -> 继续考（正常复习，略有提升）
        0 -> 完全没记起来（加大复习频率）
    实际写入的 mastery_level 会在现有基础上做一定调整。
    """
    conn = get_connection()
    c = conn.cursor()

    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 先取出当前 mastery_level
    c.execute("SELECT mastery_level FROM cards WHERE id = ?", (card_id,))
    row = c.fetchone()
    old_mastery = row[0] if row and row[0] is not None else 0

    # 根据用户自评结果调整掌握度
    if new_mastery_level == 2:
        # 已经烂熟于心：直接提升到 5
        updated_mastery = 5
    elif new_mastery_level == 1:
        # 继续考：在原有基础上小幅提升
        updated_mastery = min(5, old_mastery + 1)
    elif new_mastery_level == 0:
        # 完全没记起来：拉低掌握度，增加推荐频率
        updated_mastery = max(0, min(old_mastery, 2) - 2) if old_mastery > 0 else 0
    else:
        # 未知取值，保持不变
        updated_mastery = old_mastery

    c.execute(
        '''
        UPDATE cards 
        SET mastery_level = ?, 
            last_reviewed_at = ?, 
            review_count = review_count + 1 
        WHERE id = ?
        ''',
        (updated_mastery, current_time, card_id),
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
