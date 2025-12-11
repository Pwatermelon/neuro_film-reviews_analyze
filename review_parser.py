"""
Парсер отзывов на фильмы с различных сайтов
"""
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote
import re

class ReviewParser:
    """Класс для парсинга отзывов на фильмы"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_imdb_movie(self, movie_name):
        """Поиск фильма на IMDb"""
        try:
            # Попытка 1: Поиск через find
            search_url = f"https://www.imdb.com/find?q={quote(movie_name)}&s=tt&ttype=ft"
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code != 200:
                print(f"Ошибка HTTP: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Различные селекторы для поиска результатов
            selectors = [
                ('td', {'class': 'result_text'}),
                ('li', {'class': 'find-result-item'}),
                ('div', {'class': 'find-result'}),
                ('a', {'href': lambda x: x and '/title/tt' in x})
            ]
            
            movie_id = None
            
            # Попытка найти через различные селекторы
            for tag, attrs in selectors:
                results = soup.find_all(tag, attrs)
                for result in results:
                    # Ищем ссылку на фильм
                    link = result.find('a', href=lambda x: x and '/title/tt' in x) if tag != 'a' else result
                    if link:
                        href = link.get('href', '') if hasattr(link, 'get') else link
                        if '/title/tt' in str(href):
                            # Извлекаем ID из URL вида /title/tt1234567/
                            parts = str(href).split('/title/tt')
                            if len(parts) > 1:
                                movie_id = 'tt' + parts[1].split('/')[0].split('?')[0]
                                if movie_id and movie_id.startswith('tt'):
                                    return movie_id
            
            # Попытка 2: Прямой поиск по тексту страницы
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/title/tt' in href and '/title/tt' in href:
                    parts = href.split('/title/tt')
                    if len(parts) > 1:
                        movie_id = 'tt' + parts[1].split('/')[0].split('?')[0]
                        if movie_id and movie_id.startswith('tt') and len(movie_id) > 2:
                            return movie_id
            
            print(f"Фильм '{movie_name}' не найден в результатах поиска")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при поиске фильма: {e}")
            return None
        except Exception as e:
            print(f"Ошибка поиска фильма: {e}")
            return None
    
    def get_imdb_reviews(self, movie_id, max_reviews=50):
        """Получение отзывов с IMDb"""
        reviews = []
        seen_texts = set()  # Для отслеживания дубликатов
        
        try:
            # URL страницы с отзывами
            reviews_url = f"https://www.imdb.com/title/{movie_id}/reviews"
            response = self.session.get(reviews_url, timeout=15)
            
            if response.status_code != 200:
                print(f"Ошибка HTTP при получении отзывов: {response.status_code}")
                return reviews
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Удаляем навигационные элементы и скрипты
            for element in soup.find_all(['nav', 'header', 'footer', 'script', 'style', 'aside']):
                element.decompose()
            
            # Различные селекторы для поиска отзывов (в порядке приоритета)
            review_selectors = [
                ('div', {'class': 'lister-item-content'}),
                ('div', {'class': 'review-container'}),
                ('div', {'class': 'ipl-review'}),
                ('div', {'class': lambda x: x and 'review' in x.lower()}),
            ]
            
            review_containers = []
            for tag, attrs in review_selectors:
                containers = soup.find_all(tag, attrs)
                if containers:
                    # Фильтруем контейнеры - проверяем, что они содержат текст отзыва
                    filtered_containers = []
                    for container in containers:
                        # Пропускаем контейнеры в навигации
                        if container.find_parent(['nav', 'header', 'footer']):
                            continue
                        
                        # Проверяем наличие текста отзыва
                        text_elem = container.find('div', class_='text') or container.find('div', class_='content')
                        if text_elem:
                            text = text_elem.get_text(strip=True)
                            # Проверяем, что это не навигационный текст
                            nav_keywords = ['menu', 'release calendar', 'top 250', 'browse movies']
                            if not any(keyword in text.lower()[:100] for keyword in nav_keywords):
                                if len(text) > 50:
                                    filtered_containers.append(container)
                    
                    if filtered_containers:
                        review_containers = filtered_containers[:max_reviews]
                        break
            
            # Если не нашли через селекторы, ищем по структуре страницы
            if not review_containers:
                # Ищем все div, которые могут содержать отзывы
                all_divs = soup.find_all('div', class_=lambda x: x and ('review' in x.lower() or 'content' in x.lower()))
                for div in all_divs:
                    # Пропускаем навигационные элементы
                    if div.find_parent(['nav', 'header', 'footer']):
                        continue
                    
                    text = div.get_text(strip=True)
                    if 100 < len(text) < 5000:  # Подходящая длина для отзыва
                        # Проверяем, что это похоже на отзыв, а не навигация
                        nav_keywords = ['menu', 'release calendar', 'top 250', 'browse movies', 'box office']
                        if any(keyword in text.lower()[:100] for keyword in nav_keywords):
                            continue
                        
                        review_keywords = ['film', 'movie', 'фильм', 'character', 'plot', 'story', 'actor']
                        if any(keyword in text.lower() for keyword in review_keywords):
                            review_containers.append(div)
                            if len(review_containers) >= max_reviews:
                                break
            
            # Обрабатываем контейнеры и проверяем на дубликаты
            seen_texts = set()  # Для отслеживания уже добавленных текстов
            
            for container in review_containers[:max_reviews]:
                try:
                    # Текст отзыва - пробуем разные селекторы
                    text_elem = None
                    text_selectors = [
                        container.find('div', class_='text'),
                        container.find('div', class_='content'),
                        container.find('div', class_='review-text'),
                        container.find('div', {'class': lambda x: x and 'text' in x.lower()}),
                    ]
                    
                    # Удаляем скрытые элементы и навигацию перед поиском
                    for hidden in container.find_all(['nav', 'header', 'footer', 'script', 'style']):
                        hidden.decompose()
                    
                    for selector in text_selectors:
                        if selector:
                            # Удаляем ссылки и навигацию из текста
                            for nav in selector.find_all(['a', 'nav', 'header', 'footer']):
                                nav.decompose()
                            
                            text = selector.get_text(separator=' ', strip=True)
                            
                            # Фильтруем текст, который не является отзывом
                            # Исключаем навигационные тексты
                            nav_keywords = ['menu', 'release calendar', 'top 250', 'browse movies', 
                                          'box office', 'showtimes', 'news', 'community', 'help']
                            if any(keyword in text.lower()[:200] for keyword in nav_keywords):
                                continue
                            
                            # Проверяем, что текст похож на отзыв (содержит слова о фильме)
                            review_keywords = ['film', 'movie', 'фильм', 'character', 'plot', 'story', 
                                              'actor', 'director', 'сюжет', 'актер', 'режиссер']
                            if len(text) > 50 and any(keyword in text.lower() for keyword in review_keywords):
                                text_elem = selector
                                break
                    
                    # Если не нашли через селекторы, ищем текст напрямую в контейнере
                    if not text_elem:
                        # Ищем все параграфы и div с текстом
                        paragraphs = container.find_all(['p', 'div'])
                        for p in paragraphs:
                            # Пропускаем навигационные элементы
                            if p.find_parent(['nav', 'header', 'footer']):
                                continue
                            
                            text = p.get_text(separator=' ', strip=True)
                            
                            # Фильтруем навигационные тексты
                            nav_keywords = ['menu', 'release calendar', 'top 250', 'browse movies']
                            if any(keyword in text.lower()[:100] for keyword in nav_keywords):
                                continue
                            
                            # Проверяем, что это похоже на отзыв
                            if len(text) > 100 and len(text) < 5000:
                                review_keywords = ['film', 'movie', 'фильм', 'character', 'plot', 'story']
                                if any(keyword in text.lower() for keyword in review_keywords):
                                    text_elem = p
                                    break
                    
                    if not text_elem:
                        continue
                    
                    # Очищаем текст от лишних элементов
                    review_text = text_elem.get_text(separator=' ', strip=True)
                    
                    # Дополнительная очистка - удаляем повторяющиеся пробелы
                    review_text = ' '.join(review_text.split())
                    
                    # Проверяем минимальную длину и отсутствие навигационных фраз
                    if len(review_text) < 50:
                        continue
                    
                    nav_phrases = ['menu movies', 'release calendar', 'top 250 movies', 
                                  'most popular movies', 'browse movies by genre']
                    if any(phrase in review_text.lower()[:150] for phrase in nav_phrases):
                        continue
                    
                    # Рейтинг (если есть) - пробуем разные селекторы
                    rating = None
                    rating_selectors = [
                        container.find('span', class_='rating-other-user-rating'),
                        container.find('span', class_='ipl-rating-star__rating'),
                        container.find('span', class_='rating'),
                        container.find('div', class_='ipl-rating-star'),
                    ]
                    
                    for rating_elem in rating_selectors:
                        if rating_elem:
                            rating_text = rating_elem.get_text(strip=True)
                            # Извлекаем число из текста с помощью regex
                            numbers = re.findall(r'\d+', rating_text)
                            if numbers:
                                try:
                                    rating = int(numbers[0])
                                    if rating > 10:
                                        rating = rating // 10
                                    if 1 <= rating <= 10:
                                        break
                                except:
                                    pass
                        
                        # Ищем вложенный span
                        if rating_elem:
                            rating_spans = rating_elem.find_all('span')
                            for rating_span in rating_spans:
                                span_text = rating_span.get_text(strip=True)
                                numbers = re.findall(r'\d+', span_text)
                                if numbers:
                                    try:
                                        rating = int(numbers[0])
                                        if rating > 10:
                                            rating = rating // 10
                                        if 1 <= rating <= 10:
                                            break
                                    except:
                                        pass
                            if rating and 1 <= rating <= 10:
                                break
                    
                    # Автор - пробуем разные селекторы
                    author = "Аноним"
                    author_selectors = [
                        container.find('span', class_='display-name-link'),
                        container.find('a', class_='display-name-link'),
                        container.find('span', class_='author'),
                    ]
                    
                    for author_elem in author_selectors:
                        if author_elem:
                            author = author_elem.get_text(strip=True)
                            if author:
                                break
                    
                    # Финальная проверка перед добавлением отзыва
                    if not review_text or len(review_text) < 50:
                        continue
                    
                    # Проверяем, что это не навигационный текст
                    review_lower = review_text.lower()
                    nav_indicators = [
                        'menu movies', 'release calendar', 'top 250 movies',
                        'most popular movies', 'browse movies by genre',
                        'top box office', 'showtimes', 'news', 'community'
                    ]
                    
                    # Если первые 200 символов содержат навигационные фразы - пропускаем
                    if any(indicator in review_lower[:200] for indicator in nav_indicators):
                        continue
                    
                    # Проверяем, что текст содержит слова, характерные для отзывов
                    review_words = ['film', 'movie', 'фильм', 'character', 'plot', 'story', 
                                   'actor', 'director', 'scene', 'ending', 'performance',
                                   'сюжет', 'актер', 'режиссер', 'сцена', 'финал']
                    
                    # Если текст не содержит ни одного слова о фильме - пропускаем
                    if not any(word in review_lower for word in review_words):
                        # Но если текст достаточно длинный и не содержит навигации, возможно это отзыв
                        if len(review_text) < 200:
                            continue
                    
                    # Проверяем, что текст не является просто списком ссылок
                    if review_text.count('http') > 2 or review_text.count('www.') > 2:
                        continue
                    
                    # Проверка на дубликаты
                    review_text_normalized = review_text.strip().lower()
                    
                    # Проверяем точное совпадение
                    if review_text_normalized in seen_texts:
                        continue
                    
                    # Проверяем совпадение первых 150 символов (для случаев, когда отзывы обрезаны одинаково)
                    text_start = review_text_normalized[:150] if len(review_text_normalized) > 150 else review_text_normalized
                    if text_start in seen_texts:
                        continue
                    
                    # Проверяем похожесть с уже добавленными отзывами
                    is_duplicate = False
                    for seen_text in seen_texts:
                        # Для коротких текстов проверяем полное совпадение
                        if len(review_text_normalized) < 200 and len(seen_text) < 200:
                            if review_text_normalized == seen_text:
                                is_duplicate = True
                                break
                        else:
                            # Для длинных текстов проверяем схожесть
                            similarity = self._text_similarity(review_text_normalized, seen_text)
                            if similarity > 0.85:  # 85% схожести считается дубликатом
                                is_duplicate = True
                                break
                    
                    if is_duplicate:
                        continue
                    
                    # Добавляем текст в множество для проверки дубликатов
                    seen_texts.add(review_text_normalized)
                    seen_texts.add(text_start)
                    
                    # Все проверки пройдены - добавляем отзыв
                    reviews.append({
                        'text': review_text,
                        'rating': rating,
                        'author': author
                    })
                except Exception as e:
                    continue
            
            print(f"Получено {len(reviews)} отзывов с IMDb")
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при получении отзывов: {e}")
        except Exception as e:
            print(f"Ошибка получения отзывов: {e}")
        
        return reviews
    
    def _text_similarity(self, text1, text2):
        """Вычисление схожести двух текстов (0.0 - 1.0)"""
        if not text1 or not text2:
            return 0.0
        
        # Простой алгоритм схожести на основе общих слов
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Вычисляем коэффициент Жаккара
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def get_movie_reviews(self, movie_name, max_reviews=50):
        """Основной метод для получения отзывов по названию фильма"""
        print(f"Поиск фильма '{movie_name}'...")
        
        # Поиск фильма
        movie_id = self.search_imdb_movie(movie_name)
        
        if not movie_id:
            print("Фильм не найден на IMDb. Используются синтетические отзывы для демонстрации.")
            # Возвращаем синтетические отзывы для демонстрации
            return self.get_synthetic_reviews(movie_name, max_reviews)
        
        print(f"Найден фильм с ID: {movie_id}")
        print("Получение отзывов...")
        
        # Получение отзывов
        reviews = self.get_imdb_reviews(movie_id, max_reviews)
        
        # Если получили мало отзывов или не получили вообще, добавляем синтетические
        if len(reviews) < max_reviews:
            needed = max_reviews - len(reviews)
            print(f"Получено {len(reviews)} отзывов. Добавляю {needed} синтетических...")
            synthetic = self.get_synthetic_reviews(movie_name, needed)
            reviews.extend(synthetic)
        
        return reviews
    
    def get_synthetic_reviews(self, movie_name, count=30):
        """Генерация синтетических отзывов для демонстрации (на английском)"""
        positive_templates = [
            f"Excellent film '{movie_name}'! I really enjoyed the plot and acting. Highly recommend to everyone.",
            f"Amazing movie '{movie_name}'! The emotions are overwhelming, must watch.",
            f"Great film '{movie_name}' with an interesting story and good direction. One of the best films of the year.",
            f"Wonderful film '{movie_name}'! Watched it in one breath, very impressive.",
            f"Outstanding work by the director in '{movie_name}'. The film is top notch, must see!",
            f"Incredibly captivating film '{movie_name}'! Highly recommend to everyone.",
            f"Excellent drama '{movie_name}' with deep meaning. Very impressive.",
            f"Amazing acting in '{movie_name}'! The film is simply magnificent.",
            f"Brilliant movie '{movie_name}'! The storytelling is excellent and performances are top notch.",
            f"This is a masterpiece! '{movie_name}' exceeded all my expectations.",
        ]
        
        negative_templates = [
            f"Boring film '{movie_name}'. Not recommended, expected more.",
            f"Very disappointed with '{movie_name}'. Poor acting and weak plot.",
            f"Bad movie '{movie_name}'. Not worth watching, wasted time.",
            f"Weak script in '{movie_name}'. The film did not meet expectations.",
            f"Very predictable and boring film '{movie_name}'. Not recommended.",
            f"Disappointment from '{movie_name}'. The film is not worth the time.",
            f"Boring film '{movie_name}' without an interesting story. Poor direction.",
            f"This movie '{movie_name}' was a complete waste of time. Terrible script.",
            f"I was very disappointed with '{movie_name}'. Poor storytelling and weak characters.",
        ]
        
        reviews = []
        for i in range(count):
            if i % 2 == 0 and positive_templates:
                text = random.choice(positive_templates)
                rating = random.randint(7, 10)
            else:
                text = random.choice(negative_templates)
                rating = random.randint(1, 4)
            
            reviews.append({
                'text': text,
                'rating': rating,
                'author': f'Пользователь {i+1}'
            })
        
        return reviews

