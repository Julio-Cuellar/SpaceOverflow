FROM node:24-alpine AS build
WORKDIR /workspace/web
COPY web/package*.json ./
RUN npm ci
COPY contracts /workspace/contracts
COPY web ./
ARG VITE_DATA_MODE=demo
ARG VITE_ASSISTANT_URL=/dev/ask
ARG VITE_VOICE_URL=/api/v1/voice/utterances
ARG VITE_SPEAK_URL=/api/v1/voice/speak
ARG VITE_SESSION_URL=
ENV VITE_DATA_MODE=$VITE_DATA_MODE VITE_ASSISTANT_URL=$VITE_ASSISTANT_URL VITE_VOICE_URL=$VITE_VOICE_URL VITE_SPEAK_URL=$VITE_SPEAK_URL VITE_SESSION_URL=$VITE_SESSION_URL
RUN npm run build
FROM nginx:alpine
ENV API_UPSTREAM=http://host.docker.internal:8000 ASSISTANT_UPSTREAM=http://host.docker.internal:8000
COPY docker/frontend.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /workspace/web/dist /usr/share/nginx/html
EXPOSE 80
