#!/bin/bash
# Test script for Docker containerization

set -e  # Exit on any error

echo "🐳 Testing Docker containerization for Voice Email Agent..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t voice-email-agent:test .

# Run the container in the background
echo "🚀 Starting container..."
docker run -d \
  --name voice-email-agent-test \
  -p 8000:8000 \
  -e GEMINI_API_KEY="${GEMINI_API_KEY}" \
  voice-email-agent:test

# Wait a moment for the container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Test the health endpoint
echo "🏥 Testing health endpoint..."
if curl -f http://localhost:8000/health; then
  echo "✅ Health check passed!"
else
  echo "❌ Health check failed!"
  docker logs voice-email-agent-test
  exit 1
fi

# Test the API docs endpoint
echo "📚 Testing API docs endpoint..."
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
  echo "✅ API docs accessible!"
else
  echo "⚠️  API docs not accessible (this might be expected)"
fi

# Show container logs
echo "📋 Container logs:"
docker logs voice-email-agent-test

# Cleanup
echo "🧹 Cleaning up..."
docker stop voice-email-agent-test
docker rm voice-email-agent-test

echo "🎉 Docker test completed successfully!"
echo ""
echo "Next steps:"
echo "1. Install Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/"
echo "2. Run: fly auth login"
echo "3. Run: fly launch --no-deploy"
echo "4. Set secrets: fly secrets set GEMINI_API_KEY=your_key"
echo "5. Deploy: fly deploy"
