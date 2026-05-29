// ============================================================
// frontend/src/components/chat/ChatBubble.tsx
// Burbuja de mensaje individual — usuario y asistente
// ============================================================

import React from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Animated,
} from "react-native";
import type { ChatMessage } from "../../types";

interface Props {
  message: ChatMessage;
}

export function ChatBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      {/* Avatar asistente */}
      {!isUser && (
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>🏔</Text>
        </View>
      )}

      <View
        style={[
          styles.bubble,
          isUser ? styles.bubbleUser : styles.bubbleAssistant,
        ]}
      >
        {/* Contenido del mensaje o indicador de carga */}
        {message.isLoading ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color="#6C8EBF" />
            <Text style={styles.loadingText}>Pensando...</Text>
          </View>
        ) : (
          <Text
            style={[
              styles.text,
              isUser ? styles.textUser : styles.textAssistant,
            ]}
          >
            {message.content}
          </Text>
        )}

        {/* Advertencias de seguridad */}
        {message.safetyWarnings && message.safetyWarnings.length > 0 && (
          <View style={styles.warningBox}>
            <Text style={styles.warningIcon}>⚠️</Text>
            {message.safetyWarnings.map((w, i) => (
              <Text key={i} style={styles.warningText}>
                {w}
              </Text>
            ))}
          </View>
        )}

        {/* Fuentes del conocimiento */}
        {message.sources && message.sources.length > 0 && (
          <Text style={styles.sources}>
            Fuentes: {message.sources.join(", ")}
          </Text>
        )}

        {/* Timestamp */}
        <Text
          style={[styles.time, isUser ? styles.timeUser : styles.timeAssistant]}
        >
          {message.timestamp.toLocaleTimeString("es-BO", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    marginVertical: 4,
    paddingHorizontal: 12,
    alignItems: "flex-end",
  },
  rowUser: {
    justifyContent: "flex-end",
  },
  rowAssistant: {
    justifyContent: "flex-start",
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#E8F0FE",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 8,
  },
  avatarText: {
    fontSize: 16,
  },
  bubble: {
    maxWidth: "78%",
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 1,
  },
  bubbleUser: {
    backgroundColor: "#2563EB",
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: "#FFFFFF",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  text: {
    fontSize: 15,
    lineHeight: 22,
  },
  textUser: {
    color: "#FFFFFF",
  },
  textAssistant: {
    color: "#1F2937",
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 2,
  },
  loadingText: {
    color: "#6B7280",
    fontSize: 14,
    fontStyle: "italic",
  },
  warningBox: {
    marginTop: 8,
    backgroundColor: "#FEF3C7",
    borderRadius: 8,
    padding: 8,
    borderLeftWidth: 3,
    borderLeftColor: "#F59E0B",
  },
  warningIcon: {
    fontSize: 12,
    marginBottom: 2,
  },
  warningText: {
    fontSize: 12,
    color: "#92400E",
    lineHeight: 17,
  },
  sources: {
    marginTop: 6,
    fontSize: 11,
    color: "#9CA3AF",
    fontStyle: "italic",
  },
  time: {
    fontSize: 11,
    marginTop: 4,
  },
  timeUser: {
    color: "rgba(255,255,255,0.65)",
    textAlign: "right",
  },
  timeAssistant: {
    color: "#9CA3AF",
  },
});
