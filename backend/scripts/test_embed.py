import torch
from transformers import AutoTokenizer, AutoModel

model_id = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Loading {model_id} via HuggingFace transformers...")

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id)

def get_embedding(text: str):
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        # Mean pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)
        # Normalize
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()

emb = get_embedding("Test weather guidance text")
print(f"Success! Vector length: {len(emb)}")
