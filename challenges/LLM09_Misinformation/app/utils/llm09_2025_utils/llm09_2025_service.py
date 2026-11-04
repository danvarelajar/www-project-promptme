from flask import jsonify

from app.utils.llm09_2025_utils.llm_utils import query_llm


def process_user_input_llm09(user_message):
    return jsonify({"reply": query_llm(user_message)})
