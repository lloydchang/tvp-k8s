import express from 'express';
import fetch from 'node-fetch';

export const router = express.Router();

router.use(express.json());

router.all('*', async (req, res) => {
  const fastApiServiceUrl = process.env.FASTAPI_SERVICE_URL || 'http://fastapi-service:8000';
  const targetUrl = `${fastApiServiceUrl}${req.path}`;
  
  try {
    // Forward original headers but ensure content-type is set for JSON body
    const headers = { ...req.headers };
    if (req.body) {
      headers['Content-Type'] = 'application/json';
    }
    delete headers.host; // Remove host header as it would be incorrect for the target

    const response = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: req.body ? JSON.stringify(req.body) : null,
    });

    // Check if response is JSON before parsing
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      res.status(response.status).json(data);
    } else {
      // For non-JSON responses, forward the raw response
      const data = await response.text();
      res.status(response.status)
         .set('Content-Type', contentType || 'text/plain')
         .send(data);
    }
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ 
      error: 'An error occurred while proxying the request',
      message: error.message 
    });
  }
});
