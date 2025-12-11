"""
Flask приложение для анализа тональности отзывов на фильмы
"""
from flask import Flask, render_template, request, jsonify
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
import pickle
import os
from review_parser import ReviewParser

app = Flask(__name__)

# Параметры модели
MAX_LEN = 200
MAX_WORDS = 10000

# Загрузка модели и токенизатора
model = None
tokenizer = None

def load_model():
    """Загрузка модели и токенизатора"""
    global model, tokenizer
    
    if model is None:
        try:
            model = keras.models.load_model('model/sentiment_classifier.h5')
            print("Модель успешно загружена")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            print("Убедитесь, что модель обучена. Запустите train_model.py")
            return False
    
    if tokenizer is None:
        try:
            with open('model/tokenizer.pkl', 'rb') as f:
                tokenizer = pickle.load(f)
            print("Токенизатор успешно загружен")
        except Exception as e:
            print(f"Ошибка загрузки токенизатора: {e}")
            return False
    
    return True

def predict_sentiment(text):
    """Предсказание тональности текста"""
    if model is None or tokenizer is None:
        return None
    
    # Токенизация
    sequence = tokenizer.texts_to_sequences([text])
    padded = pad_sequences(sequence, maxlen=MAX_LEN, padding='post', truncating='post')
    
    # Предсказание
    prediction = model.predict(padded, verbose=0)[0][0]
    
    return {
        'sentiment': 'positive' if prediction > 0.5 else 'negative',
        'confidence': float(prediction) if prediction > 0.5 else float(1 - prediction),
        'score': float(prediction)
    }

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Анализ отзывов на фильм"""
    data = request.get_json()
    movie_name = data.get('movie_name', '').strip()
    max_reviews = int(data.get('max_reviews', 50))
    
    if not movie_name:
        return jsonify({'error': 'Название фильма не указано'}), 400
    
    # Проверка загрузки модели
    if not load_model():
        return jsonify({'error': 'Модель не загружена. Обучите модель сначала.'}), 500
    
    try:
        # Получение отзывов
        parser = ReviewParser()
        print(f"Начинаю поиск отзывов для фильма: {movie_name}")
        reviews = parser.get_movie_reviews(movie_name, max_reviews)
        
        if not reviews:
            return jsonify({
                'error': 'Не удалось получить отзывы. Возможно, фильм не найден или сайт недоступен. Попробуйте другое название фильма.'
            }), 500
        
        # Анализ тональности каждого отзыва
        analyzed_reviews = []
        positive_count = 0
        negative_count = 0
        
        for review in reviews:
            sentiment_result = predict_sentiment(review['text'])
            
            if sentiment_result:
                review['sentiment'] = sentiment_result['sentiment']
                review['confidence'] = round(sentiment_result['confidence'] * 100, 2)
                review['score'] = sentiment_result['score']
                
                if sentiment_result['sentiment'] == 'positive':
                    positive_count += 1
                else:
                    negative_count += 1
            else:
                review['sentiment'] = 'unknown'
                review['confidence'] = 0
            
            analyzed_reviews.append(review)
        
        # Статистика
        total = len(analyzed_reviews)
        positive_percent = round((positive_count / total) * 100, 2) if total > 0 else 0
        negative_percent = round((negative_count / total) * 100, 2) if total > 0 else 0
        
        result = {
            'movie_name': movie_name,
            'total_reviews': total,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'positive_percent': positive_percent,
            'negative_percent': negative_percent,
            'reviews': analyzed_reviews
        }
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        error_details = str(e)
        print(f"Ошибка при анализе: {error_details}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Ошибка обработки: {error_details}. Убедитесь, что модель обучена и интернет-соединение активно.'
        }), 500

@app.route('/health')
def health():
    """Проверка состояния сервера"""
    model_loaded = model is not None
    tokenizer_loaded = tokenizer is not None
    
    return jsonify({
        'status': 'ok' if (model_loaded and tokenizer_loaded) else 'not_ready',
        'model_loaded': model_loaded,
        'tokenizer_loaded': tokenizer_loaded
    })

if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs('model', exist_ok=True)
    
    # Загрузка модели при старте
    load_model()
    
    print("Запуск Flask приложения...")
    print("Откройте http://localhost:5000 в браузере")
    app.run(debug=True, host='0.0.0.0', port=5000)

