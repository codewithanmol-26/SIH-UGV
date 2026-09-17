FROM node:22-slim AS build
WORKDIR /app/frontend
ARG VITE_API_BASE=http://localhost:8000/api
ARG VITE_WS_URL=ws://localhost:8000/ws/telemetry
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_WS_URL=$VITE_WS_URL
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM node:22-slim
WORKDIR /app
RUN npm install -g serve@14
COPY --from=build /app/frontend/dist ./dist
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
