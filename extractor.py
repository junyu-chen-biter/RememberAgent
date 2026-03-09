import os
import json
from pypdf import PdfReader
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def read_pdf(file):
    """
    Reads text content from a PDF file.
    """
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_knowledge(text):
    """
    Extracts knowledge points from text using OpenAI API.
    Returns a list of dictionaries [{'q': '...', 'a': '...'}, ...].
    """
    
    system_prompt = "你是一个助教。从文本中提取关键记忆点，并整理为 Question 和 Answer 对。返回标准的 JSON 格式 list，例如 [{'q': '...', 'a': '...'}, ...]"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125", 
            messages=[
                {"role": "system", "content": "你是一个助教。从文本中提取关键记忆点，并整理为 Question 和 Answer 对。请直接返回一个JSON对象，其中包含一个名为 'knowledge_points' 的键，对应的值是 [{'q': '...', 'a': '...'}, ...] 的列表。"},
                {"role": "user", "content": f"请从以下文本中提取知识点：\n\n{text[:15000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        
        content = completion.choices[0].message.content
        data = json.loads(content)
        
        if "knowledge_points" in data:
            return data["knowledge_points"]
        
        # Fallback: check if any value is a list
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    return value
        
        return []
            
    except Exception as e:
        print(f"Error extracting knowledge: {e}")
        return []

def evaluate_answer(question, standard_answer, user_answer):
    """
    Evaluates the user's answer against the standard answer.
    Returns a dictionary {'score': int, 'feedback': str}.
    """
    system_prompt = "标准答案是 A，用户回答是 B。请给用户打分（0-5分，0完全不会，5完全掌握），并给出简短评价。请返回 JSON 格式，包含 'score' (整数) 和 'feedback' (字符串) 两个字段。"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"问题：{question}\n\n标准答案 (A)：{standard_answer}\n\n用户回答 (B)：{user_answer}"}
            ],
            response_format={ "type": "json_object" }
        )
        
        content = completion.choices[0].message.content
        data = json.loads(content)
        
        return {
            "score": data.get("score", 0),
            "feedback": data.get("feedback", "无评价")
        }
            
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {
            "score": 0,
            "feedback": "评分失败，请稍后重试。"
        }
