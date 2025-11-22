FROM eclipse-temurin:17

WORKDIR /app

RUN apt-get update && apt-get install -y wget unzip && rm -rf /var/lib/apt/lists/*

# Download NCANode 3.4.0
RUN wget --user-agent="Mozilla/5.0" -O NCANode.zip https://github.com/ncanode-kz/NCANode/releases/download/3.4.0/NCANode-3.4.0.zip \
    && unzip NCANode.zip \
    && rm NCANode.zip

# Expose port
EXPOSE 14579

# Run the JAR
CMD ["java", "-jar", "NCANode-3.4.0.jar"]
