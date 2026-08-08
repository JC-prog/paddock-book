import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';

const CHAT_API_URL = 'http://localhost:8000/v1/chat';
const FIRST_EVENT_TIMEOUT_MS = 10_000;

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  private readonly authService = inject(AuthService);

  streamReply(text: string): Observable<string> {
    return new Observable<string>((subscriber) => {
      const controller = new AbortController();
      let timeoutId: ReturnType<typeof setTimeout> | undefined = setTimeout(
        () => controller.abort(),
        FIRST_EVENT_TIMEOUT_MS
      );

      const clearFirstEventTimeout = () => {
        if (timeoutId !== undefined) {
          clearTimeout(timeoutId);
          timeoutId = undefined;
        }
      };

      // Races an operation against the abort signal so a hung/silent
      // connection is treated as an error even though the mock/real stream
      // itself may never independently observe the abort (see research.md).
      const raceAgainstAbort = <T>(promise: Promise<T>): Promise<T> =>
        new Promise<T>((resolve, reject) => {
          if (controller.signal.aborted) {
            reject(new Error('chat request timed out'));
            return;
          }
          const onAbort = () => reject(new Error('chat request timed out'));
          controller.signal.addEventListener('abort', onAbort, { once: true });
          promise.then(
            (value) => {
              controller.signal.removeEventListener('abort', onAbort);
              resolve(value);
            },
            (err) => {
              controller.signal.removeEventListener('abort', onAbort);
              reject(err);
            }
          );
        });

      (async () => {
        try {
          const token = this.authService.getAccessToken();
          const headers: Record<string, string> = { 'Content-Type': 'application/json' };
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
          }

          const response = await raceAgainstAbort(
            fetch(CHAT_API_URL, {
              method: 'POST',
              headers,
              body: JSON.stringify({ message: text })
            })
          );

          if (!response.ok || !response.body) {
            throw new Error('chat request failed');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await raceAgainstAbort(reader.read());
            clearFirstEventTimeout();
            if (done) {
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            for (const line of lines) {
              if (line.startsWith('data:')) {
                subscriber.next(line.slice('data:'.length).trim());
              }
            }
          }

          subscriber.complete();
        } catch (err) {
          subscriber.error(err);
        } finally {
          clearFirstEventTimeout();
        }
      })();

      return () => {
        clearFirstEventTimeout();
        controller.abort();
      };
    });
  }
}
