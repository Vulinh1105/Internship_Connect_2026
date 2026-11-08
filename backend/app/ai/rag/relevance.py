import re

from app.ai.providers.embedding import normalize,words


IGNORED={"la","gi","nao","nhung","cac","voi","nhu","the","bao","nhieu","co","cua","va","trong"}


MINIMUM_WORK_AGE_QUERY="độ tuổi lao động tối thiểu"


def asks_minimum_work_age(question):
    text=normalize(question)
    return bool(
        re.search(r"\btuoi\b",text)
        and re.search(r"\b(di lam|lam viec|lao dong)\b",text)
        and re.search(r"\b(bao nhieu|may tuoi|toi thieu|it nhat|nho nhat|tu tuoi nao|tu do tuoi nao)\b",text)
        and not re.search(r"\d+\s*tuoi\b",text)
    )


def supports_minimum_work_age(quote):
    text=normalize(quote)
    return bool(
        re.search(r"\b(lao dong toi thieu|tuoi toi thieu.{0,45}(di lam|lam viec|lao dong))\b",text)
        and re.search(r"(?<!\d)\d{1,2}\s+tuoi\b",text)
    )


def best_passage(query,text,*,minimum_work_age=False):
    terms=set(query)-IGNORED
    phrases={pair for pair in zip(query,query[1:]) if not IGNORED.intersection(pair)}
    long_phrases={triple for triple in zip(query,query[1:],query[2:]) if not IGNORED.intersection(triple)}
    sentences=list(re.finditer(r".+?(?:(?<!\d)[.!?;](?=\s|$)|$)",text,re.S))
    scope=("doi","tuong","ap","dung")
    asks_scope={("doi","tuong"),("ap","dung")}<=phrases
    best_score=0
    best_quote=""
    for i,sentence in enumerate(sentences):
        sentence_words=words(sentence.group())
        tokens=[word for word in sentence_words if word not in IGNORED]
        overlap=terms.intersection(tokens)
        if len(overlap)<2:
            continue
        # Prefer terms that occur together over scattered matches in long passages.
        nearby=max(len(terms.intersection(tokens[j:j+14])) for j in range(max(1,len(tokens)-13)))
        score=3*nearby+len(overlap)+2*len(phrases.intersection(zip(sentence_words,sentence_words[1:])))
        score+=8*len(long_phrases.intersection(zip(sentence_words,sentence_words[1:],sentence_words[2:])))
        if asks_scope and scope in zip(sentence_words,sentence_words[1:],sentence_words[2:],sentence_words[3:]):
            score+=18
            if re.search(r"\b1[.)]\s",sentence.group()):
                score+=8
        if score<=best_score:
            continue
        end=sentence.end()
        if re.search(r"\b1[.)]\s",sentence.group()):
            for following in sentences[i+1:i+5]:
                if not re.match(r"\s*\d+[.)]\s",following.group()) or following.end()-sentence.start()>560:
                    break
                end=following.end()
        quote=text[sentence.start():min(end,sentence.start()+560)].strip()
        if len(quote)>=8 and (not minimum_work_age or supports_minimum_work_age(quote)):
            best_score,best_quote=score,quote
    return best_score,best_quote
