import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

const CHAT_PROVIDER_API = 'http://localhost:8000/v1/admin/settings/chat-provider';

type LoadState = 'loading' | 'loaded' | 'error';
type Provider = 'ollama' | 'bedrock' | 'openai_compatible';

const PROVIDER_LABELS: Record<Provider, string> = {
  ollama: 'Ollama',
  bedrock: 'AWS Bedrock',
  openai_compatible: 'OpenAI-compatible'
};

export interface ChatProviderConfig {
  active_provider: Provider;
  ollama_model_override: string | null;
  bedrock_model: string | null;
  openai_compatible_base_url: string | null;
  openai_compatible_model: string | null;
  openai_compatible_api_key_set: boolean;
}

@Component({
  selector: 'app-chat-provider',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="mx-auto mt-16 max-w-md px-4">
      <h1 class="mb-6 text-xl font-semibold">Chat Provider</h1>

      @switch (loadState()) {
        @case ('loading') {
          <p>Loading current configuration…</p>
        }
        @case ('error') {
          <p class="text-sm text-red-600" data-testid="chat-provider-load-error">
            Could not load the current configuration.
          </p>
        }
        @case ('loaded') {
          <p class="mb-4 text-sm" data-testid="active-provider-display">
            Active provider: <strong>{{ activeProviderLabel() }}</strong>
          </p>

          <label class="mb-2 block text-sm font-medium">Provider</label>
          <select
            [(ngModel)]="selectedProvider"
            name="selectedProvider"
            data-testid="provider-select"
            class="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="ollama">Ollama</option>
            <option value="bedrock">AWS Bedrock</option>
            <option value="openai_compatible">OpenAI-compatible</option>
          </select>

          @if (selectedProvider === 'bedrock') {
            <label class="mb-2 block text-sm font-medium">Bedrock model identifier</label>
            <input
              [(ngModel)]="bedrockModel"
              name="bedrockModel"
              placeholder="e.g. anthropic.claude-3-5-sonnet-v2"
              data-testid="bedrock-model-input"
              class="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          }

          @if (selectedProvider === 'openai_compatible') {
            <label class="mb-2 block text-sm font-medium">Base URL</label>
            <input
              [(ngModel)]="openaiBaseUrl"
              name="openaiBaseUrl"
              placeholder="https://api.openai.com/v1"
              data-testid="openai-base-url-input"
              class="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />

            <label class="mb-2 block text-sm font-medium">
              API key
              @if (existingKeySaved()) {
                <span class="font-normal text-slate-500">(a key is already saved — leave blank to keep it)</span>
              }
            </label>
            <input
              [(ngModel)]="openaiApiKey"
              name="openaiApiKey"
              type="password"
              placeholder="Paste API key"
              data-testid="openai-api-key-input"
              class="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />

            <label class="mb-2 block text-sm font-medium">Model</label>
            <input
              [(ngModel)]="openaiModel"
              name="openaiModel"
              placeholder="e.g. gpt-4o-mini"
              data-testid="openai-model-input"
              class="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          }

          <button
            type="button"
            (click)="save()"
            data-testid="save-button"
            class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >Save</button>

          @if (saveError()) {
            <p class="mt-3 text-sm text-red-600" data-testid="chat-provider-save-error">{{ saveError() }}</p>
          }
        }
      }
    </div>
  `
})
export class ChatProviderComponent implements OnInit {
  private readonly http = inject(HttpClient);

  private readonly _loadState = signal<LoadState>('loading');
  private readonly _config = signal<ChatProviderConfig | null>(null);
  private readonly _saveError = signal<string | null>(null);

  readonly loadState = this._loadState.asReadonly();
  readonly saveError = this._saveError.asReadonly();

  selectedProvider: Provider = 'ollama';
  bedrockModel = '';
  openaiBaseUrl = '';
  // Never prefilled from a GET/PUT response — the backend never returns
  // a saved key's value (FR-011), so this only ever holds a NEW value
  // the admin is actively typing in this session.
  openaiApiKey = '';
  openaiModel = '';

  activeProviderLabel(): string {
    return PROVIDER_LABELS[this._config()?.active_provider ?? 'ollama'];
  }

  existingKeySaved(): boolean {
    return this._config()?.openai_compatible_api_key_set ?? false;
  }

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.http.get<ChatProviderConfig>(CHAT_PROVIDER_API).subscribe({
      next: (config) => {
        this._applyConfig(config);
        this._loadState.set('loaded');
      },
      error: () => this._loadState.set('error')
    });
  }

  save(): void {
    this._saveError.set(null);
    const updates: Record<string, unknown> = { active_provider: this.selectedProvider };
    if (this.selectedProvider === 'bedrock' && this.bedrockModel) {
      updates['bedrock_model'] = this.bedrockModel;
    }
    if (this.selectedProvider === 'openai_compatible') {
      if (this.openaiBaseUrl) {
        updates['openai_compatible_base_url'] = this.openaiBaseUrl;
      }
      if (this.openaiModel) {
        updates['openai_compatible_model'] = this.openaiModel;
      }
      // Omitted (not sent as an empty string) unless the admin actually
      // typed a new value — a partial-update PUT leaves an omitted field
      // untouched, which is what lets reactivating a previously
      // configured provider skip re-entering its key (FR-015).
      if (this.openaiApiKey) {
        updates['openai_compatible_api_key'] = this.openaiApiKey;
      }
    }

    this.http.put<ChatProviderConfig>(CHAT_PROVIDER_API, updates).subscribe({
      next: (config) => this._applyConfig(config),
      error: (err) => {
        // Translates the backend's 409 (contracts/admin-api.md) into a
        // readable message rather than showing a raw HTTP body.
        this._saveError.set(
          err?.error?.detail ?? 'This provider needs more information before it can be activated.'
        );
      }
    });
  }

  private _applyConfig(config: ChatProviderConfig): void {
    this._config.set(config);
    this.selectedProvider = config.active_provider;
    this.bedrockModel = config.bedrock_model ?? '';
    this.openaiBaseUrl = config.openai_compatible_base_url ?? '';
    this.openaiModel = config.openai_compatible_model ?? '';
    // Never populated from a response — see the field's own comment.
    this.openaiApiKey = '';
  }
}
