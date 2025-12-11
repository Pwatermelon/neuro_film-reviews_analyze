"""
Скрипт для обучения модели анализа тональности отзывов
Использует датасет отзывов на фильмы IMDb
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
import pandas as pd
import os
import pickle

# Параметры
MAX_WORDS = 10000
MAX_LEN = 200
EMBEDDING_DIM = 128

def load_imdb_data():
    """
    Загрузка датасета IMDb отзывов
    Если датасет недоступен, создается синтетический датасет
    """
    print("Загрузка данных для обучения...")
    
    try:
        # Попытка загрузить встроенный датасет IMDb
        (x_train, y_train), (x_test, y_test) = keras.datasets.imdb.load_data(
            num_words=MAX_WORDS
        )
        
        # Получение словаря
        word_index = keras.datasets.imdb.get_word_index()
        reverse_word_index = {v: k for k, v in word_index.items()}
        
        # Конвертация обратно в текст для токенизации
        def decode_review(encoded):
            return ' '.join([reverse_word_index.get(i - 3, '?') for i in encoded if i > 3])
        
        # Декодирование небольшой выборки для создания токенизатора
        print("Подготовка токенизатора...")
        sample_texts = [decode_review(x_train[i]) for i in range(min(1000, len(x_train)))]
        
        # Создание токенизатора
        tokenizer = Tokenizer(num_words=MAX_WORDS, oov_token="<OOV>")
        tokenizer.fit_on_texts(sample_texts)
        
        # Токенизация данных
        x_train_seq = tokenizer.texts_to_sequences([decode_review(x) for x in x_train])
        x_test_seq = tokenizer.texts_to_sequences([decode_review(x) for x in x_test])
        
        x_train_pad = pad_sequences(x_train_seq, maxlen=MAX_LEN, padding='post', truncating='post')
        x_test_pad = pad_sequences(x_test_seq, maxlen=MAX_LEN, padding='post', truncating='post')
        
        return (x_train_pad, y_train), (x_test_pad, y_test), tokenizer
        
    except Exception as e:
        print(f"Ошибка загрузки IMDb датасета: {e}")
        print("Создание синтетического датасета...")
        return create_synthetic_data()

def create_synthetic_data():
    """Создание синтетического датасета отзывов на английском языке"""
    # Положительные отзывы (на английском)
    positive_reviews = [
        "Excellent film! I really enjoyed the plot and acting.",
        "Amazing movie! I highly recommend it to everyone.",
        "Great film with an interesting story and good direction.",
        "One of the best movies I've ever seen. Highly recommended!",
        "Wonderful film! The emotions are overwhelming, must watch.",
        "Outstanding work by the director and actors. The film is top notch!",
        "Incredibly captivating film! Watched it in one breath.",
        "Excellent drama with deep meaning. Very impressive.",
        "Amazing acting! The film is simply magnificent.",
        "One of the most interesting films of the year. Must see!",
        "This movie is absolutely fantastic! Great storytelling and performances.",
        "I loved every minute of this film. The cinematography is stunning.",
        "Brilliant movie with excellent character development.",
        "This is a masterpiece! The plot twists are incredible.",
        "Outstanding performances from all actors. Highly entertaining.",
        "One of the best films I've watched recently. Truly amazing!",
        "The direction is superb and the story is engaging throughout.",
        "This movie exceeded all my expectations. Simply wonderful!",
        "Great film with powerful emotions and strong narrative.",
        "I was completely captivated from start to finish. Excellent work!"
    ] * 1250
    
    # Отрицательные отзывы (на английском)
    negative_reviews = [
        "Boring and predictable film. Not recommended.",
        "Very disappointed. Expected more from this movie.",
        "Poor acting and weak plot. Not worth watching.",
        "Boring film without an interesting story. Wasted time.",
        "Very weak film. Did not meet expectations.",
        "Poor direction and boring plot. Not recommended.",
        "Disappointing. The film is not worth the time.",
        "Weak script and poor acting.",
        "Very predictable and boring film.",
        "Did not like the film. Weak plot, actors perform poorly.",
        "This movie was a complete waste of time. Terrible script.",
        "I was very disappointed with this film. Poor storytelling.",
        "The acting is terrible and the plot makes no sense.",
        "Boring and unoriginal. I expected much better.",
        "This film is poorly made with weak character development.",
        "Not worth watching. The story is confusing and boring.",
        "The direction is weak and the actors seem disinterested.",
        "I found this movie to be very dull and unengaging.",
        "Poor quality film with no redeeming qualities.",
        "This was one of the worst movies I've ever seen."
    ] * 1250
    
    all_reviews = positive_reviews + negative_reviews
    labels = [1] * len(positive_reviews) + [0] * len(negative_reviews)
    
    # Создание токенизатора
    tokenizer = Tokenizer(num_words=MAX_WORDS, oov_token="<OOV>")
    tokenizer.fit_on_texts(all_reviews)
    
    # Токенизация
    sequences = tokenizer.texts_to_sequences(all_reviews)
    padded = pad_sequences(sequences, maxlen=MAX_LEN, padding='post', truncating='post')
    
    # Разделение на train/test
    split_idx = int(len(padded) * 0.8)
    x_train = padded[:split_idx]
    x_test = padded[split_idx:]
    y_train = np.array(labels[:split_idx])
    y_test = np.array(labels[split_idx:])
    
    return (x_train, y_train), (x_test, y_test), tokenizer

def create_model():
    """Создание модели для анализа тональности"""
    model = keras.Sequential([
        layers.Embedding(MAX_WORDS, EMBEDDING_DIM, input_length=MAX_LEN),
        layers.GlobalAveragePooling1D(),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def train_model():
    """Обучение модели"""
    # Загрузка данных
    (x_train, y_train), (x_test, y_test), tokenizer = load_imdb_data()
    
    print(f"Обучающая выборка: {x_train.shape}")
    print(f"Тестовая выборка: {x_test.shape}")
    
    # Создание модели
    model = create_model()
    model.summary()
    
    # Callbacks
    callbacks = [
        keras.callbacks.ModelCheckpoint(
            'model/sentiment_classifier.h5',
            save_best_only=True,
            monitor='val_accuracy',
            mode='max'
        ),
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            patience=5,
            restore_best_weights=True
        )
    ]
    
    # Обучение
    print("\nНачало обучения...")
    history = model.fit(
        x_train, y_train,
        batch_size=128,
        epochs=10,
        validation_data=(x_test, y_test),
        callbacks=callbacks,
        verbose=1
    )
    
    # Оценка модели
    print("\nОценка модели на тестовой выборке...")
    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)
    print(f"Точность на тестовой выборке: {test_accuracy:.4f}")
    
    # Сохранение модели и токенизатора
    model.save('model/sentiment_classifier.h5')
    
    with open('model/tokenizer.pkl', 'wb') as f:
        pickle.dump(tokenizer, f)
    
    print("\nМодель сохранена в model/sentiment_classifier.h5")
    print("Токенизатор сохранен в model/tokenizer.pkl")
    
    return model, tokenizer

if __name__ == '__main__':
    # Создание директории для модели
    os.makedirs('model', exist_ok=True)
    
    # Обучение
    model, tokenizer = train_model()

