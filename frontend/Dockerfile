FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build Next.js app
RUN npm run build

# Expose port (Next.js default 3000)
EXPOSE 3000

# Start command
CMD ["npm", "start"]
