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

# 安装 wget 用于健康检查和等待 MySQL
RUN apk add --no-cache wget

COPY --from=builder /app/target/hr-employee.jar app.jar

# 等待 MySQL 就绪的脚本
COPY wait-for-mysql.sh /wait-for-mysql.sh
RUN chmod +x /wait-for-mysql.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

EXPOSE 8080
ENTRYPOINT ["/wait-for-mysql.sh"]
CMD ["java", "-jar", "app.jar"]
