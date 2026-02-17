import "./env.js"; // Carrega .env ANTES de qualquer outro import

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

import express from "express";
import swaggerUi from "swagger-ui-express";

import { getCacheStats } from "./services/cache.js";
import { checkHealth } from "./services/qdrant.js";
import askRouter from "./routes/ask.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(join(__dirname, "../public")));

// Swagger
const swaggerDoc = JSON.parse(
  readFileSync(join(__dirname, "../swagger.json"), "utf-8")
);
app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(swaggerDoc));

// Rotas
app.use("/api/ask", askRouter);

app.get("/api/health", async (_req, res) => {
  try {
    const qdrant = await checkHealth();
    const cache = getCacheStats();
    res.json({ status: "ok", qdrant, cache });
  } catch (err) {
    res.status(500).json({ status: "error", message: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`API rodando em http://localhost:${PORT}`);
  console.log(`Chat UI em http://localhost:${PORT}`);
  console.log(`Swagger UI em http://localhost:${PORT}/api-docs`);
});

export default app;
