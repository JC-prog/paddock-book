import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';

const ADMIN_API_BASE = 'http://localhost:8000/v1/admin';

type LoadState = 'loading' | 'loaded' | 'error';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [],
  template: `
    <div class="mx-auto mt-16 max-w-sm px-4">
      <h1 class="mb-6 text-xl font-semibold">Admin</h1>

      @switch (loadState()) {
        @case ('loading') {
          <p>Loading current setting…</p>
        }
        @case ('error') {
          <p class="text-sm text-red-600" data-testid="admin-error">Could not load the current setting.</p>
        }
        @case ('loaded') {
          <label class="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              data-testid="log-to-file-toggle"
              [checked]="logToFile()"
              (change)="onToggle($event)"
            />
            Also write logs to a local file
          </label>
        }
      }

      @if (saveError()) {
        <p class="mt-3 text-sm text-red-600" data-testid="admin-save-error">
          Could not save the new setting.
        </p>
      }
    </div>
  `
})
export class AdminComponent implements OnInit {
  private readonly http = inject(HttpClient);

  private readonly _loadState = signal<LoadState>('loading');
  private readonly _logToFile = signal(false);
  private readonly _saveError = signal(false);

  readonly loadState = this._loadState.asReadonly();
  readonly logToFile = this._logToFile.asReadonly();
  readonly saveError = this._saveError.asReadonly();

  ngOnInit(): void {
    this.http.get<{ log_to_file: boolean }>(`${ADMIN_API_BASE}/settings/log-destination`).subscribe({
      next: (response) => {
        this._logToFile.set(response.log_to_file);
        this._loadState.set('loaded');
      },
      error: () => this._loadState.set('error')
    });
  }

  onToggle(event: Event): void {
    const newValue = (event.target as HTMLInputElement).checked;
    this._saveError.set(false);

    this.http
      .put<{ log_to_file: boolean }>(`${ADMIN_API_BASE}/settings/log-destination`, {
        log_to_file: newValue
      })
      .subscribe({
        next: (response) => this._logToFile.set(response.log_to_file),
        error: () => {
          this._saveError.set(true);
          (event.target as HTMLInputElement).checked = this._logToFile();
        }
      });
  }
}
