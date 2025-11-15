"""
Seed data for onboarding assessments and lesson content across languages.

This module centralizes vocabulary translations and assessment questions so we
can consistently generate lessons for multiple languages (Spanish, French,
German, Korean, etc.). It is intentionally framework-agnostic: no direct
references to Django models so it can be safely reused by migrations,
management commands, or future scripts.
"""

from __future__ import annotations

from typing import Dict, List

LESSON_CARD_DATA: Dict[str, Dict] = {
    'shapes': {
        'title_template': 'Shapes in {language}',
        'description_template': 'Learn essential shape names in {language}',
        'slug': 'shapes',
        'order': 1,
        'category': 'Shapes',
        'quiz_count': 5,
        'xp_value': 100,
        'cards': [
            {
                'front': 'Circle',
                'translations': {
                    'Spanish': 'Círculo',
                    'French': 'Cercle',
                    'German': 'Kreis',
                    'Korean': '원 (won)',
                },
            },
            {
                'front': 'Square',
                'translations': {
                    'Spanish': 'Cuadrado',
                    'French': 'Carré',
                    'German': 'Quadrat',
                    'Korean': '정사각형 (jeong-sagak-hyeong)',
                },
            },
            {
                'front': 'Triangle',
                'translations': {
                    'Spanish': 'Triángulo',
                    'French': 'Triangle',
                    'German': 'Dreieck',
                    'Korean': '삼각형 (sam-gak-hyeong)',
                },
            },
            {
                'front': 'Rectangle',
                'translations': {
                    'Spanish': 'Rectángulo',
                    'French': 'Rectangle',
                    'German': 'Rechteck',
                    'Korean': '직사각형 (jik-sagak-hyeong)',
                },
            },
            {
                'front': 'Oval',
                'translations': {
                    'Spanish': 'Óvalo',
                    'French': 'Ovale',
                    'German': 'Oval',
                    'Korean': '타원형 (ta-won-hyeong)',
                },
            },
            {
                'front': 'Star',
                'translations': {
                    'Spanish': 'Estrella',
                    'French': 'Étoile',
                    'German': 'Stern',
                    'Korean': '별 (byeol)',
                },
            },
            {
                'front': 'Heart',
                'translations': {
                    'Spanish': 'Corazón',
                    'French': 'Cœur',
                    'German': 'Herz',
                    'Korean': '하트 (hateu)',
                },
            },
            {
                'front': 'Diamond',
                'translations': {
                    'Spanish': 'Diamante',
                    'French': 'Losange',
                    'German': 'Raute',
                    'Korean': '마름모 (mareum-mo)',
                },
            },
        ],
    },
    'colors': {
        'title_template': 'Colors in {language}',
        'description_template': 'Learn everyday colors in {language}',
        'slug': 'colors',
        'order': 2,
        'category': 'Colors',
        'quiz_count': 8,
        'xp_value': 120,
        'cards': [
            {
                'front': 'Red',
                'translations': {
                    'Spanish': 'Rojo',
                    'French': 'Rouge',
                    'German': 'Rot',
                    'Korean': '빨간색 (ppalgan-saek)',
                },
            },
            {
                'front': 'Blue',
                'translations': {
                    'Spanish': 'Azul',
                    'French': 'Bleu',
                    'German': 'Blau',
                    'Korean': '파란색 (paran-saek)',
                },
            },
            {
                'front': 'Yellow',
                'translations': {
                    'Spanish': 'Amarillo',
                    'French': 'Jaune',
                    'German': 'Gelb',
                    'Korean': '노란색 (noran-saek)',
                },
            },
            {
                'front': 'Green',
                'translations': {
                    'Spanish': 'Verde',
                    'French': 'Vert',
                    'German': 'Grün',
                    'Korean': '초록색 (chorok-saek)',
                },
            },
            {
                'front': 'Purple',
                'translations': {
                    'Spanish': 'Morado',
                    'French': 'Violet',
                    'German': 'Lila',
                    'Korean': '보라색 (bora-saek)',
                },
            },
            {
                'front': 'Orange',
                'translations': {
                    'Spanish': 'Naranja',
                    'French': 'Orange',
                    'German': 'Orange',
                    'Korean': '주황색 (juhwang-saek)',
                },
            },
            {
                'front': 'Pink',
                'translations': {
                    'Spanish': 'Rosa',
                    'French': 'Rose',
                    'German': 'Rosa',
                    'Korean': '분홍색 (bunhong-saek)',
                },
            },
            {
                'front': 'Brown',
                'translations': {
                    'Spanish': 'Marrón',
                    'French': 'Marron',
                    'German': 'Braun',
                    'Korean': '갈색 (galsaek)',
                },
            },
            {
                'front': 'Black',
                'translations': {
                    'Spanish': 'Negro',
                    'French': 'Noir',
                    'German': 'Schwarz',
                    'Korean': '검은색 (geomeun-saek)',
                },
            },
            {
                'front': 'White',
                'translations': {
                    'Spanish': 'Blanco',
                    'French': 'Blanc',
                    'German': 'Weiß',
                    'Korean': '하얀색 (hayan-saek)',
                },
            },
        ],
    },
}


ONBOARDING_QUESTION_SETS: Dict[str, List[Dict]] = {
    'French': [
        {
            'question_number': 1,
            'difficulty_level': 'A1',
            'question_text': "What is the French word for 'hello'?",
            'option_a': 'Salut',
            'option_b': 'Bonjour',
            'option_c': 'Merci',
            'option_d': 'Au revoir',
            'correct_answer': 'B',
            'explanation': "'Bonjour' is the standard greeting meaning 'hello' or 'good day'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 2,
            'difficulty_level': 'A1',
            'question_text': "How do you say 'thank you' in French?",
            'option_a': 'Pardon',
            'option_b': 'Merci',
            'option_c': 'S’il vous plaît',
            'option_d': 'Bonsoir',
            'correct_answer': 'B',
            'explanation': "'Merci' translates directly to 'thank you'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 3,
            'difficulty_level': 'A1',
            'question_text': "Which phrase means 'I am'?",
            'option_a': 'Je suis',
            'option_b': 'Tu es',
            'option_c': 'Il est',
            'option_d': 'Nous sommes',
            'correct_answer': 'A',
            'explanation': "'Je suis' is the first person singular form of 'être' (to be).",
            'difficulty_points': 1,
        },
        {
            'question_number': 4,
            'difficulty_level': 'A1',
            'question_text': "Which of these is a color in French?",
            'option_a': 'Livre',
            'option_b': 'Rouge',
            'option_c': 'Table',
            'option_d': 'Chaise',
            'correct_answer': 'B',
            'explanation': "'Rouge' means 'red'. The other words mean book, table, and chair.",
            'difficulty_points': 1,
        },
        {
            'question_number': 5,
            'difficulty_level': 'A2',
            'question_text': "How do you say 'I ate' in French?",
            'option_a': 'Je mange',
            'option_b': "J'ai mangé",
            'option_c': 'Je mangerai',
            'option_d': 'Je mangeais',
            'correct_answer': 'B',
            'explanation': "“J'ai mangé” is the passé composé (simple past) form meaning 'I ate'.",
            'difficulty_points': 2,
        },
        {
            'question_number': 6,
            'difficulty_level': 'A2',
            'question_text': "Complete the sentence: 'Hier, je ___ au parc.' (Yesterday I went to the park.)",
            'option_a': 'vais',
            'option_b': 'suis allé',
            'option_c': 'irai',
            'option_d': 'allais',
            'correct_answer': 'B',
            'explanation': "'Je suis allé' is the correct past form with the auxiliary 'être' for aller.",
            'difficulty_points': 2,
        },
        {
            'question_number': 7,
            'difficulty_level': 'A2',
            'question_text': "What does 'Il fait beau' mean?",
            'option_a': "It's raining",
            'option_b': 'The weather is nice',
            'option_c': "It's very cold",
            'option_d': "It's windy",
            'correct_answer': 'B',
            'explanation': "'Il fait beau' describes pleasant weather.",
            'difficulty_points': 2,
        },
        {
            'question_number': 8,
            'difficulty_level': 'B1',
            'question_text': "Choose the correct comparative: 'Ma sœur est ___ que moi.' (My sister is taller than me.)",
            'option_a': 'plus grande',
            'option_b': 'plus grand',
            'option_c': 'aussi grande',
            'option_d': 'très grande',
            'correct_answer': 'A',
            'explanation': "Comparatives use 'plus + adjective + que'; 'grande' agrees with 'sœur'.",
            'difficulty_points': 3,
        },
        {
            'question_number': 9,
            'difficulty_level': 'B1',
            'question_text': "Complete with the subjunctive: 'Il faut que tu ___ tôt.' (You must come early.)",
            'option_a': 'viens',
            'option_b': 'venir',
            'option_c': 'viennes',
            'option_d': 'viendras',
            'correct_answer': 'C',
            'explanation': "'Il faut que' triggers the subjunctive: 'tu viennes'.",
            'difficulty_points': 3,
        },
        {
            'question_number': 10,
            'difficulty_level': 'B1',
            'question_text': "Which sentence correctly uses a conditional structure?",
            'option_a': "Si je travaille, je dormais.",
            'option_b': "Si j'avais le temps, je voyagerais.",
            'option_c': 'Je voyagerai si j’avais le temps.',
            'option_d': "Si j'ai le temps, je voyagerais.",
            'correct_answer': 'B',
            'explanation': "A proper conditional pairs 'si' + imperfect with conditional: 'je voyagerais'.",
            'difficulty_points': 3,
        },
    ],
    'German': [
        {
            'question_number': 1,
            'difficulty_level': 'A1',
            'question_text': "What is the German word for 'hello'?",
            'option_a': 'Hallo',
            'option_b': 'Tschüss',
            'option_c': 'Danke',
            'option_d': 'Bitte',
            'correct_answer': 'A',
            'explanation': "'Hallo' is the common informal greeting meaning 'hello'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 2,
            'difficulty_level': 'A1',
            'question_text': "How do you say 'thank you' in German?",
            'option_a': 'Bitte',
            'option_b': 'Auf Wiedersehen',
            'option_c': 'Guten Morgen',
            'option_d': 'Danke',
            'correct_answer': 'D',
            'explanation': "'Danke' translates to 'thank you'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 3,
            'difficulty_level': 'A1',
            'question_text': "Which phrase means 'I am'?",
            'option_a': 'Ich bin',
            'option_b': 'Du bist',
            'option_c': 'Er ist',
            'option_d': 'Wir sind',
            'correct_answer': 'A',
            'explanation': "'Ich bin' is the first person singular of 'sein' (to be).",
            'difficulty_points': 1,
        },
        {
            'question_number': 4,
            'difficulty_level': 'A1',
            'question_text': "Which of these is a color in German?",
            'option_a': 'Buch',
            'option_b': 'Rot',
            'option_c': 'Stuhl',
            'option_d': 'Fenster',
            'correct_answer': 'B',
            'explanation': "'Rot' means 'red'. The other words mean book, chair, and window.",
            'difficulty_points': 1,
        },
        {
            'question_number': 5,
            'difficulty_level': 'A2',
            'question_text': "How do you say 'I ate' in German?",
            'option_a': 'Ich esse',
            'option_b': 'Ich habe gegessen',
            'option_c': 'Ich werde essen',
            'option_d': 'Ich aß',
            'correct_answer': 'B',
            'explanation': "'Ich habe gegessen' is the perfect tense commonly used for past actions.",
            'difficulty_points': 2,
        },
        {
            'question_number': 6,
            'difficulty_level': 'A2',
            'question_text': "Complete: 'Morgen ___ ich ins Kino gehen.' (Tomorrow I will go to the cinema.)",
            'option_a': 'gehe',
            'option_b': 'ging',
            'option_c': 'werde',
            'option_d': 'bin gegangen',
            'correct_answer': 'C',
            'explanation': "Future tense in German often uses 'werden' + infinitive.",
            'difficulty_points': 2,
        },
        {
            'question_number': 7,
            'difficulty_level': 'A2',
            'question_text': "What does 'Es ist warm' mean?",
            'option_a': "It's raining",
            'option_b': "It's windy",
            'option_c': "It's warm",
            'option_d': "It's cloudy",
            'correct_answer': 'C',
            'explanation': "'Es ist warm' literally means 'It is warm'.",
            'difficulty_points': 2,
        },
        {
            'question_number': 8,
            'difficulty_level': 'B1',
            'question_text': "Choose the correct comparative: 'Mein Bruder ist ___ als ich.' (My brother is taller than me.)",
            'option_a': 'größer',
            'option_b': 'groß',
            'option_c': 'am groß',
            'option_d': 'größte',
            'correct_answer': 'A',
            'explanation': "Comparatives add '‑er': 'größer als'.",
            'difficulty_points': 3,
        },
        {
            'question_number': 9,
            'difficulty_level': 'B1',
            'question_text': "Which sentence has the correct subordinate clause word order?",
            'option_a': 'Ich weiß, du kommst morgen.',
            'option_b': 'Ich weiß, dass du morgen kommst.',
            'option_c': 'Ich weiß dass du kommst morgen.',
            'option_d': 'Ich weiß, dass du kommst morgen.',
            'correct_answer': 'B',
            'explanation': "Subordinate clauses send the verb to the end: 'dass du morgen kommst'.",
            'difficulty_points': 3,
        },
        {
            'question_number': 10,
            'difficulty_level': 'B1',
            'question_text': "Which conditional sentence is correct?",
            'option_a': 'Wenn ich Zeit habe, würde ich mehr lesen.',
            'option_b': 'Wenn ich Zeit hätte, würde ich mehr lesen.',
            'option_c': 'Wenn ich Zeit hätte, ich würde mehr lesen.',
            'option_d': 'Wenn ich Zeit habe würde ich mehr lesen.',
            'correct_answer': 'B',
            'explanation': "Unreal conditionals use 'hätte' + 'würde' construction.",
            'difficulty_points': 3,
        },
    ],
    'Korean': [
        {
            'question_number': 1,
            'difficulty_level': 'A1',
            'question_text': "Which expression means 'hello' in Korean?",
            'option_a': '안녕하세요',
            'option_b': '감사합니다',
            'option_c': '잘 자요',
            'option_d': '미안합니다',
            'correct_answer': 'A',
            'explanation': "'안녕하세요' (annyeonghaseyo) is the polite way to say hello.",
            'difficulty_points': 1,
        },
        {
            'question_number': 2,
            'difficulty_level': 'A1',
            'question_text': "How do you say 'thank you' in Korean?",
            'option_a': '사랑해요',
            'option_b': '괜찮아요',
            'option_c': '감사합니다',
            'option_d': '안녕히 가세요',
            'correct_answer': 'C',
            'explanation': "'감사합니다' (gamsahamnida) means 'thank you'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 3,
            'difficulty_level': 'A1',
            'question_text': "Which sentence means 'I am a student'?",
            'option_a': '저는 학생입니다',
            'option_b': '저는 선생님입니다',
            'option_c': '저는 친구입니다',
            'option_d': '저는 회사원입니다',
            'correct_answer': 'A',
            'explanation': "'저는 학생입니다' translates to 'I am a student'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 4,
            'difficulty_level': 'A1',
            'question_text': "Which of these is a color in Korean?",
            'option_a': '책',
            'option_b': '파란색',
            'option_c': '학교',
            'option_d': '친구',
            'correct_answer': 'B',
            'explanation': "'파란색' (paran-saek) means 'blue'.",
            'difficulty_points': 1,
        },
        {
            'question_number': 5,
            'difficulty_level': 'A2',
            'question_text': "Which sentence means 'I ate rice'?",
            'option_a': '밥을 먹었어요',
            'option_b': '밥을 먹을 거예요',
            'option_c': '밥을 먹고 있어요',
            'option_d': '밥을 먹지 않아요',
            'correct_answer': 'A',
            'explanation': "'먹었어요' is the past tense meaning 'ate'.",
            'difficulty_points': 2,
        },
        {
            'question_number': 6,
            'difficulty_level': 'A2',
            'question_text': "Complete: '내일 저는 도서관에 ___.' (Tomorrow I will go to the library.)",
            'option_a': '갑니다',
            'option_b': '가요',
            'option_c': '갈 거예요',
            'option_d': '갔어요',
            'correct_answer': 'C',
            'explanation': "'갈 거예요' indicates future intention ('will go').",
            'difficulty_points': 2,
        },
        {
            'question_number': 7,
            'difficulty_level': 'A2',
            'question_text': "What does '날씨가 좋아요' mean?",
            'option_a': 'It is raining',
            'option_b': 'It is too hot',
            'option_c': 'The weather is nice',
            'option_d': 'It is snowing',
            'correct_answer': 'C',
            'explanation': "'좋아요' means 'is good'—the weather is pleasant.",
            'difficulty_points': 2,
        },
        {
            'question_number': 8,
            'difficulty_level': 'B1',
            'question_text': "Fill in the blank: '한국어를 ___ 공부하면 더 잘하게 돼요.' (If you study Korean ___, you get better.)",
            'option_a': '꾸준히',
            'option_b': '빨리',
            'option_c': '조용히',
            'option_d': '갑자기',
            'correct_answer': 'A',
            'explanation': "'꾸준히' means 'consistently', fitting the conditional meaning.",
            'difficulty_points': 3,
        },
        {
            'question_number': 9,
            'difficulty_level': 'B1',
            'question_text': "Choose the polite request meaning 'Could you help me?'",
            'option_a': '도와줄래?',
            'option_b': '도와주세요',
            'option_c': '도와줄 거야',
            'option_d': '도와준다',
            'correct_answer': 'B',
            'explanation': "'도와주세요' is the standard polite request form.",
            'difficulty_points': 3,
        },
        {
            'question_number': 10,
            'difficulty_level': 'B1',
            'question_text': "Complete the conditional: '시간이 있으면 친구를 ___.' (If I have time, I will meet my friend.)",
            'option_a': '만났어요',
            'option_b': '만나요',
            'option_c': '만날 거예요',
            'option_d': '만나고 있어요',
            'correct_answer': 'C',
            'explanation': "'만날 거예요' expresses the future result of the condition.",
            'difficulty_points': 3,
        },
    ],
}


def build_lesson_blueprints(language: str) -> List[Dict]:
    """
    Generate lesson metadata, flashcards, and quiz questions for a language.

    Args:
        language: English language name (e.g., 'French').

    Returns:
        List of dicts describing lessons ready to persist.
    """
    blueprints: List[Dict] = []

    for key, config in LESSON_CARD_DATA.items():
        cards_for_language = []
        for idx, card in enumerate(config['cards'], start=1):
            translation = card['translations'].get(language)
            if not translation:
                continue
            cards_for_language.append({
                'order': idx,
                'front_text': card['front'],
                'back_text': translation,
                'image_url': '',
            })

        if not cards_for_language:
            continue

        lesson_slug = f"{config['slug']}-{language.lower()}"

        blueprint = {
            'key': key,
            'title': config['title_template'].format(language=language),
            'description': config['description_template'].format(language=language),
            'slug': lesson_slug,
            'language': language,
            'order': config['order'],
            'category': config['category'],
            'lesson_type': 'flashcard',
            'xp_value': config['xp_value'],
            'flashcards': cards_for_language,
            'quiz_questions': _build_quiz_questions(
                cards_for_language, language, key, config.get('quiz_count', len(cards_for_language))
            ),
        }
        blueprints.append(blueprint)

    return blueprints


def _build_quiz_questions(cards: List[Dict], language: str, key: str, quiz_count: int) -> List[Dict]:
    """Build deterministic quiz questions from the provided flashcards."""
    questions: List[Dict] = []
    subset = cards[:quiz_count]

    for order, card in enumerate(subset, start=1):
        distractors = [c['back_text'] for c in cards if c['back_text'] != card['back_text']]
        options = [card['back_text']] + distractors[:3]

        questions.append({
            'order': order,
            'question': f'What is "{card["front_text"]}" in {language}?',
            'options': options,
            'correct_index': 0,
        })

    return questions

