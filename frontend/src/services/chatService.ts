// ============================================================
// frontend/src/services/chatService.ts
// Servicio de comunicación con el backend para el chatbot
// ============================================================

import { ChatRequest, ChatResponse } from '../types';

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8080';
const TIMEOUT_MS = 15_000;

class ChatService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // El token JWT se agrega aquí cuando el usuario está autenticado
          // 'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ChatServiceError(
          error.detail ?? `Error ${response.status}`,
          response.status
        );
      }

      return (await response.json()) as ChatResponse;
    } catch (err) {
      if (err instanceof ChatServiceError) throw err;
      if ((err as Error).name === 'AbortError') {
        throw new ChatServiceError('La solicitud tardó demasiado. Intenta de nuevo.', 408);
      }
      throw new ChatServiceError('Sin conexión. Verifica tu internet.', 0);
    } finally {
      clearTimeout(timeout);
    }
  }
}

export class ChatServiceError extends Error {
  constructor(message: string, public readonly statusCode: number) {
    super(message);
    this.name = 'ChatServiceError';
  }
}

export const chatService = new ChatService(API_BASE);