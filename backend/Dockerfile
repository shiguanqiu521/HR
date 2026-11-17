# 构建阶段：使用 Maven 编译
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY settings.xml /root/.m2/settings.xml
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn clean package -DskipTests -B

# JaCoCo agent：供接口用例的覆盖率归因使用。文件进镜像但不自动挂载，
# 只有 compose 显式设置 JAVA_TOOL_OPTIONS 时才会生效（见 docker-compose.coverage.yml）。
ARG JACOCO_VERSION=0.8.11
RUN mvn -B -q dependency:copy \
        -Dartifact=org.jacoco:org.jacoco.agent:${JACOCO_VERSION}:jar:runtime \
        -DoutputDirectory=/opt/jacoco \
    && mv /opt/jacoco/org.jacoco.agent-*.jar /opt/jacoco/jacocoagent.jar

# 运行阶段：使用精简 JRE 镜像
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/hr-employee.jar app.jar
COPY --from=builder /opt/jacoco/jacocoagent.jar /opt/jacoco/jacocoagent.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
