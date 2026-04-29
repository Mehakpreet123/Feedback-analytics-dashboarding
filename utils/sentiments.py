# sentiments.py
from textblob import TextBlob

def analyze_sentiment(comment):
    """
    Returns sentiment label and polarity score
    """
    if not comment or str(comment).strip() == "":
        return "Neutral", 0.0

    analysis = TextBlob(comment)
    polarity = analysis.sentiment.polarity

    if polarity > 0.1:
        label = "Positive"
    elif polarity < -0.1:
        label = "Negative"
    else:
        label = "Neutral"

    return label, polarity