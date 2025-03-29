import express from 'express';
import fetch from 'node-fetch';

export const router = express.Router();

router.use(express.json());

router.all('*', async (req, res) => {
  const targetUrl = `http://fastapi-service:8000${req.path}`;
  
  const response = await fetch(targetUrl, {
    method: req.method,
    headers: { 'Content-Type': 'application/json' },
    body: req.body ? JSON.stringify(req.body) : null,
  });

  const data = await response.json();
  res.status(response.status).json(data);
});
