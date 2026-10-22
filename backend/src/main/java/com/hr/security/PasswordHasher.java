package com.hr.security;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.spec.InvalidKeySpecException;
import java.util.HexFormat;

/**
 * 口令哈希：PBKDF2-HMAC-SHA256 加盐多轮迭代，仅用 JDK 自带能力。
 */
public final class PasswordHasher {

    private static final String ALGORITHM = "PBKDF2WithHmacSHA256";
    private static final int ITERATIONS = 60_000;
    private static final int KEY_LENGTH_BITS = 256;
    private static final int SALT_BYTES = 16;
    private static final SecureRandom RANDOM = new SecureRandom();

    private PasswordHasher() {
    }

    public static String newSalt() {
        byte[] salt = new byte[SALT_BYTES];
        RANDOM.nextBytes(salt);
        return HexFormat.of().formatHex(salt);
    }

    public static String hash(String rawPassword, String saltHex) {
        try {
            PBEKeySpec spec = new PBEKeySpec(
                    rawPassword.toCharArray(),
                    HexFormat.of().parseHex(saltHex),
                    ITERATIONS,
                    KEY_LENGTH_BITS);
            byte[] derived = SecretKeyFactory.getInstance(ALGORITHM).generateSecret(spec).getEncoded();
            spec.clearPassword();
            return HexFormat.of().formatHex(derived);
        } catch (NoSuchAlgorithmException | InvalidKeySpecException | IllegalArgumentException e) {
            throw new IllegalStateException("口令哈希计算失败", e);
        }
    }

    /**
     * 定长比较，避免通过响应时间差异推测哈希前缀。
     */
    public static boolean matches(String rawPassword, String saltHex, String expectedHash) {
        if (rawPassword == null || saltHex == null || expectedHash == null) {
            return false;
        }
        byte[] actual = HexFormat.of().parseHex(hash(rawPassword, saltHex));
        byte[] expected;
        try {
            expected = HexFormat.of().parseHex(expectedHash);
        } catch (IllegalArgumentException e) {
            return false;
        }
        return MessageDigest.isEqual(actual, expected);
    }
}
