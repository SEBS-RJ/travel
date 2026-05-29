// ============================================================
// frontend/src/hooks/useChat.ts
// Hook de estado para el chatbot
// Gestiona mensajes, historial, loading y errores
// ============================================================

import { useState, useCallback, useRef } from 'react';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

import { chatService, ChatServiceError } from '../services/chatService';
import type { ChatMessage, UserContext } from '../types';

const MAX_HISTORY = 10; // Máximo de turnos a enviar al backend

export function useChat(userContext?: UserContext) {
  const [messages, setMessages]   = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  // sessionId persiste durante la vida del componente
  const sessionId = useRef<string>(uuidv4()).current;

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    setError(null);

    // Agregar mensaje del usuario inmediatamente
    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    // Placeholder de carga del asistente
    const loadingMessage: ChatMessage = {
      id: uuidv4(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);

    try {
      // Construir historial (sin el placeholder de carga)
      const history = messages
        .filter(m => !m.isLoading)
        .slice(-MAX_HISTORY)
        .map(m => ({ role: m.role, content: m.content }));

      const response = await chatService.sendMessage({
        sessionId,
        message: text.trim(),
        history,
        userContext,
        language: 'es',
      });

      const assistantMessage: ChatMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(response.timestamp),
        intent: response.intent,
        sources: response.sources,
        safetyWarnings: response.safetyWarnings,
        quickReplies: response.quickReplies,
        fallbackUsed: response.fallbackUsed,
        isLoading: false,
      };

      // Reemplazar el placeholder con la respuesta real
      setMessages(prev => [
        ...prev.filter(m => m.id !== loadingMessage.id),
        assistantMessage,
      ]);
    } catch (err) {
      const message = err instanceof ChatServiceError
        ? err.message
        : 'Ocurrió un error inesperado. Intenta de nuevo.';

      setError(message);

      // Reemplazar placeholder con mensaje de error
      setMessages(prev => [
        ...prev.filter(m => m.id !== loadingMessage.id),
        {
          id: uuidv4(),
          role: 'assistant',
          content: message,
          timestamp: new Date(),
          isLoading: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading, sessionId, userContext]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, clearChat, sessionId };
}