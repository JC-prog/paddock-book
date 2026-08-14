import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ChatProviderComponent, ChatProviderConfig } from './chat-provider.component';

const API = 'http://localhost:8000/v1/admin/settings/chat-provider';

describe('ChatProviderComponent', () => {
  let httpMock: HttpTestingController;

  function setup() {
    TestBed.configureTestingModule({
      imports: [ChatProviderComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    httpMock = TestBed.inject(HttpTestingController);

    const fixture = TestBed.createComponent(ChatProviderComponent);
    return fixture;
  }

  afterEach(() => {
    httpMock.verify();
  });

  function config(overrides: Partial<ChatProviderConfig> = {}): ChatProviderConfig {
    return {
      active_provider: 'ollama',
      ollama_model_override: null,
      bedrock_model: null,
      openai_compatible_base_url: null,
      openai_compatible_model: null,
      openai_compatible_api_key_set: false,
      ...overrides
    };
  }

  it('loads and clearly displays the currently active provider', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock.expectOne(API).flush(config({ active_provider: 'bedrock' }));
    fixture.detectChanges();

    const display = fixture.nativeElement.querySelector('[data-testid="active-provider-display"]');
    expect(display.textContent.toLowerCase()).toContain('bedrock');
  });

  it('selecting AWS Bedrock reveals a model identifier input', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(config());
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="bedrock-model-input"]')).toBeFalsy();

    fixture.componentInstance.selectedProvider = 'bedrock';
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="bedrock-model-input"]')).toBeTruthy();
  });

  it('saving Bedrock with a model identifier PUTs it and updates the displayed active provider', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(config());
    fixture.detectChanges();

    fixture.componentInstance.selectedProvider = 'bedrock';
    fixture.componentInstance.bedrockModel = 'anthropic.claude-3-5-sonnet-v2';
    fixture.componentInstance.save();

    const req = httpMock.expectOne(API);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({
      active_provider: 'bedrock',
      bedrock_model: 'anthropic.claude-3-5-sonnet-v2'
    });
    req.flush(config({ active_provider: 'bedrock', bedrock_model: 'anthropic.claude-3-5-sonnet-v2' }));
    fixture.detectChanges();

    const display = fixture.nativeElement.querySelector('[data-testid="active-provider-display"]');
    expect(display.textContent.toLowerCase()).toContain('bedrock');
  });

  it('saving Bedrock without a model identifier shows a clear inline error, not a raw HTTP body', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(config());
    fixture.detectChanges();

    fixture.componentInstance.selectedProvider = 'bedrock';
    fixture.componentInstance.bedrockModel = '';
    fixture.componentInstance.save();

    httpMock
      .expectOne(API)
      .flush(
        { detail: 'bedrock requires a model identifier before it can be activated' },
        { status: 409, statusText: 'Conflict' }
      );
    fixture.detectChanges();

    const errorEl = fixture.nativeElement.querySelector('[data-testid="chat-provider-save-error"]');
    expect(errorEl).toBeTruthy();
    expect(errorEl.textContent).toContain('model identifier');
  });

  it('selecting OpenAI-compatible reveals base URL, API key, and model inputs', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(config());
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="openai-base-url-input"]')).toBeFalsy();

    fixture.componentInstance.selectedProvider = 'openai_compatible';
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-testid="openai-base-url-input"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-testid="openai-api-key-input"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('[data-testid="openai-model-input"]')).toBeTruthy();
  });

  it('saving OpenAI-compatible with all three fields PUTs them together', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(config());
    fixture.detectChanges();

    fixture.componentInstance.selectedProvider = 'openai_compatible';
    fixture.componentInstance.openaiBaseUrl = 'https://api.openai.com/v1';
    fixture.componentInstance.openaiApiKey = 'sk-test';
    fixture.componentInstance.openaiModel = 'gpt-4o-mini';
    fixture.componentInstance.save();

    const req = httpMock.expectOne(API);
    expect(req.request.body).toEqual({
      active_provider: 'openai_compatible',
      openai_compatible_base_url: 'https://api.openai.com/v1',
      openai_compatible_api_key: 'sk-test',
      openai_compatible_model: 'gpt-4o-mini'
    });
    req.flush(
      config({
        active_provider: 'openai_compatible',
        openai_compatible_base_url: 'https://api.openai.com/v1',
        openai_compatible_model: 'gpt-4o-mini',
        openai_compatible_api_key_set: true
      })
    );
  });

  it('does not send the API key field when reactivating without retyping it, and never shows a saved key value', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne(API).flush(
      config({
        active_provider: 'ollama',
        openai_compatible_base_url: 'https://api.openai.com/v1',
        openai_compatible_model: 'gpt-4o-mini',
        openai_compatible_api_key_set: true
      })
    );
    fixture.detectChanges();

    // Base URL/model are prefilled (not secrets); the key input stays empty —
    // GET never returns the key's value (FR-011).
    expect(fixture.componentInstance.openaiApiKey).toBe('');
    const apiKeyInput = fixture.nativeElement.querySelector('[data-testid="openai-api-key-input"]');
    expect(apiKeyInput?.value ?? '').not.toContain('sk-');

    fixture.componentInstance.selectedProvider = 'openai_compatible';
    fixture.componentInstance.save();

    const req = httpMock.expectOne(API);
    expect(req.request.body).toEqual({
      active_provider: 'openai_compatible',
      openai_compatible_base_url: 'https://api.openai.com/v1',
      openai_compatible_model: 'gpt-4o-mini'
    });
  });

  it.each(['ollama', 'bedrock', 'openai_compatible'] as const)(
    'shows the active provider (%s) clearly on initial load with no user interaction at all (User Story 3)',
    (activeProvider) => {
      const fixture = setup();
      fixture.detectChanges();

      httpMock.expectOne(API).flush(config({ active_provider: activeProvider }));
      fixture.detectChanges();

      const display = fixture.nativeElement.querySelector('[data-testid="active-provider-display"]');
      expect(display).toBeTruthy();
      expect(display.textContent.length).toBeGreaterThan('Active provider:'.length);
    }
  );

  it('shows an error state when the initial load fails', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock.expectOne(API).flush({ detail: 'error' }, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(
      (fixture.nativeElement as HTMLElement).textContent?.toLowerCase()
    ).toContain('could not load');
  });
});
