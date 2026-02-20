"""한글 초성 추출 모듈."""

CHOSUNG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ",
    "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3


def extract_chosung(text: str) -> str:
    """텍스트에서 한글 초성을 추출한다. 공백 유지, 비한글은 그대로."""
    result = []
    for ch in text:
        code = ord(ch)
        if HANGUL_START <= code <= HANGUL_END:
            idx = (code - HANGUL_START) // 588
            result.append(CHOSUNG_LIST[idx])
        else:
            result.append(ch)
    return "".join(result)


def count_korean_chars(text: str) -> int:
    """텍스트 내 한글 글자 수를 센다."""
    return sum(1 for ch in text if HANGUL_START <= ord(ch) <= HANGUL_END)


if __name__ == "__main__":
    test = "그대 내게 오지 말아요"
    print(f"원문: {test}")
    print(f"초성: {extract_chosung(test)}")
    print(f"한글 수: {count_korean_chars(test)}")
