// ============================================================
// frontend/src/screens/ChatScreen.tsx
// Pantalla principal del chatbot — integra todos los componentes
// ============================================================

import React, { useRef, useEffect, useState } from "react";
import {
  View,
  FlatList,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StatusBar,
} from "react-native";

import { useChat } from "../hooks/useChat";
import { ChatBubble } from "../components/chat/ChatBubble";
import { QuickReplies } from "../components/chat/QuickReplies";
import type { ChatMessage, UserContext } from "../types";

// Mensaje de bienvenida inicial del asistente
const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "¡Hola! Soy tu asistente de turismo de Tarija 🏔️\n\n¿En qué puedo ayudarte hoy?",
  timestamp: new Date(),
  quickReplies: [
    "¿Qué visitar?",
    "Rutas seguras",
    "Planificar mi día",
    "Gastronomía típica",
  ],
};

interface Props {
  userContext?: UserContext;
}

export function ChatScreen({ userContext }: Props) {
  const { messages, isLoading, error, sendMessage } = useChat(userContext);
  const [inputText, setInputText] = useState("");
  const flatListRef = useRef<FlatList>(null);

  // Combinar bienvenida + mensajes de la sesión
  const allMessages: ChatMessage[] = [WELCOME_MESSAGE, ...messages];

  // Último mensaje con quickReplies disponible
  const lastAssistantMsg = [...allMessages]
    .reverse()
    .find((m) => m.role === "assistant" && !m.isLoading);
  const activeQuickReplies = lastAssistantMsg?.quickReplies ?? [];

  // Auto-scroll al último mensaje
  useEffect(() => {
    if (allMessages.length > 1) {
      setTimeout(
        () => flatListRef.current?.scrollToEnd({ animated: true }),
        100,
      );
    }
  }, [allMessages.length]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText("");
    await sendMessage(text);
  };

  const handleQuickReply = async (reply: string) => {
    if (isLoading) return;
    await sendMessage(reply);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>🏔️</Text>
        <View>
          <Text style={styles.headerTitle}>Asistente Turístico</Text>
          <Text style={styles.headerSubtitle}>Tarija, Bolivia</Text>
        </View>
        <View style={[styles.dot, isLoading && styles.dotLoading]} />
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
      >
        {/* Lista de mensajes */}
        <FlatList
          ref={flatListRef}
          data={allMessages}
          keyExtractor={(m) => m.id}
          renderItem={({ item }) => <ChatBubble message={item} />}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          onLayout={() => flatListRef.current?.scrollToEnd({ animated: false })}
        />

        {/* Error banner */}
        {error && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>⚠️ {error}</Text>
          </View>
        )}

        {/* Quick replies */}
        <QuickReplies
          replies={activeQuickReplies}
          onSelect={handleQuickReply}
        />

        {/* Input bar */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.input}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Pregunta sobre Tarija..."
            placeholderTextColor="#9CA3AF"
            multiline
            maxLength={500}
            onSubmitEditing={handleSend}
            blurOnSubmit={false}
            returnKeyType="send"
            editable={!isLoading}
          />
          <TouchableOpacity
            style={[
              styles.sendButton,
              (!inputText.trim() || isLoading) && styles.sendButtonDisabled,
            ]}
            onPress={handleSend}
            disabled={!inputText.trim() || isLoading}
            activeOpacity={0.8}
          >
            <Text style={styles.sendIcon}>➤</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  flex: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
    gap: 10,
  },
  headerEmoji: {
    fontSize: 28,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#6B7280",
  },
  dot: {
    marginLeft: "auto",
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#10B981",
  },
  dotLoading: {
    backgroundColor: "#F59E0B",
  },
  messageList: {
    paddingTop: 12,
    paddingBottom: 8,
  },
  errorBanner: {
    marginHorizontal: 12,
    marginBottom: 6,
    backgroundColor: "#FEE2E2",
    borderRadius: 10,
    padding: 10,
    borderLeftWidth: 3,
    borderLeftColor: "#EF4444",
  },
  errorText: {
    fontSize: 13,
    color: "#991B1B",
  },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#FFFFFF",
    borderTopWidth: 1,
    borderTopColor: "#E5E7EB",
    gap: 8,
  },
  input: {
    flex: 1,
    minHeight: 42,
    maxHeight: 100,
    backgroundColor: "#F3F4F6",
    borderRadius: 21,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: "#111827",
    lineHeight: 20,
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: "#2563EB",
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#2563EB",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 3,
  },
  sendButtonDisabled: {
    backgroundColor: "#D1D5DB",
    shadowOpacity: 0,
    elevation: 0,
  },
  sendIcon: {
    color: "#FFFFFF",
    fontSize: 16,
    marginLeft: 2,
  },
});
