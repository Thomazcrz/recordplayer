# Deploy RecordPlayer no Render

1. Crie conta em https://render.com
2. Novo serviço → Web Service → Conecte seu repositório ou envie ZIP.
3. Ambiente: Python 3.10+
4. Comando de inicialização:
   gunicorn app:app
5. Adicione variáveis de ambiente:
   REPLICATE_API_TOKEN=seu_token_aqui
   REPLICATE_MODEL_MUSIC=meta/musicgen:8e4fe22f8b934c5e87b0ab3e6a1b83a9b0a3f456
   REPLICATE_MODEL_VOICE=suno-ai/bark
   FLASK_ENV=production
   PORT=8000
6. Deploy e aguarde o Build terminar.
7. Teste em: https://recordplayer.onrender.com
