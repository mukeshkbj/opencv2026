FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter
WORKDIR /app
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server/twice ./twice
COPY server/samples ./samples
COPY --from=web /web/dist /web/dist
ENV PORT=8000 \
    AWS_LWA_READINESS_CHECK_PATH=/api/health \
    TWICE_WEB=/web/dist \
    TWICE_DATA=/tmp/data
USER 10001
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn twice.app:app --host 0.0.0.0 --port ${PORT}"]
