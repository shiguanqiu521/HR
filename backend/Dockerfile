# 构建阶段：使用 Maven 编译
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY settings.xml /root/.m2/settings.xml
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn clean package -DskipTests -B

# 运行阶段：使用精简 JRE 镜像
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/hr-employee.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
