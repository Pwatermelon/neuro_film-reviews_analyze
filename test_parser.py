"""
Тестовый скрипт для проверки работы парсера отзывов
"""
from review_parser import ReviewParser

def test_parser():
    """Тестирование парсера"""
    parser = ReviewParser()
    
    # Тестовые названия фильмов
    test_movies = [
        "The Matrix",
        "Inception",
        "Interstellar",
        "Пианист",
        "Темный рыцарь"
    ]
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПАРСЕРА ОТЗЫВОВ")
    print("=" * 60)
    
    for movie_name in test_movies:
        print(f"\n{'='*60}")
        print(f"Тестирование: {movie_name}")
        print(f"{'='*60}")
        
        try:
            # Поиск фильма
            movie_id = parser.search_imdb_movie(movie_name)
            
            if movie_id:
                print(f"✓ Фильм найден! ID: {movie_id}")
                
                # Получение отзывов
                reviews = parser.get_imdb_reviews(movie_id, max_reviews=5)
                print(f"✓ Получено отзывов: {len(reviews)}")
                
                if reviews:
                    print("\nПримеры отзывов:")
                    for i, review in enumerate(reviews[:3], 1):
                        print(f"\n{i}. Автор: {review['author']}")
                        if review.get('rating'):
                            print(f"   Рейтинг: {review['rating']}/10")
                        print(f"   Текст: {review['text'][:100]}...")
            else:
                print(f"✗ Фильм не найден на IMDb")
                print("  Используются синтетические отзывы")
                
                # Тест синтетических отзывов
                synthetic = parser.get_synthetic_reviews(movie_name, 3)
                print(f"✓ Создано синтетических отзывов: {len(synthetic)}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)

if __name__ == '__main__':
    test_parser()

