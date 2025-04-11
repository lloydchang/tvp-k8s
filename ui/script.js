document.addEventListener('DOMContentLoaded', () => {
  const statusIndicator = document.getElementById('status-indicator');
  const statusText = document.getElementById('status-text');
  
  // Check platform health status
  checkHealth();
  
  // Set up periodic health check
  setInterval(checkHealth, 60000); // Check every minute
  
  async function checkHealth() {
    try {
      const response = await fetch('/health');
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.status === 'healthy') {
          statusIndicator.className = 'status-indicator status-healthy';
          statusText.textContent = 'Platform health: OK';
        } else {
          statusIndicator.className = 'status-indicator status-unhealthy';
          statusText.textContent = 'Platform health: Degraded';
        }
      } else {
        statusIndicator.className = 'status-indicator status-unhealthy';
        statusText.textContent = 'Platform health: Error';
      }
    } catch (error) {
      console.error('Health check failed:', error);
      statusIndicator.className = 'status-indicator status-unhealthy';
      statusText.textContent = 'Platform health: Unavailable';
    }
  }
  
  // Add fade-in animation for cards
  const cards = document.querySelectorAll('.card');
  
  cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    // Stagger the animations
    setTimeout(() => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 100 * index);
  });
});