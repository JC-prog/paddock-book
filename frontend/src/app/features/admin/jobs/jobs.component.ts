import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

const JOBS_API_BASE = 'http://localhost:8000/v1/admin/jobs';
const POLL_INTERVAL_MS = 3000;

export interface JobRecord {
  id: string;
  job_type: 'download' | 'ingest';
  target: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  triggered_by_email: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="mx-auto mt-16 max-w-2xl px-4">
      <h1 class="mb-6 text-xl font-semibold">Background Jobs</h1>

      @if (loadError()) {
        <p class="mb-3 text-sm text-red-600" data-testid="jobs-load-error">Could not load jobs.</p>
      }

      <form (ngSubmit)="submitDownload()" class="mb-6">
        <h2 class="mb-2 text-sm font-medium">Download a category</h2>
        <input
          [(ngModel)]="categoryId"
          name="categoryId"
          placeholder="Category ID"
          data-testid="download-category-input"
          class="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          data-testid="download-submit"
          class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >Start download</button>
        @if (downloadError()) {
          <p class="mt-2 text-sm text-red-600" data-testid="download-error">{{ downloadError() }}</p>
        }
      </form>

      <form (ngSubmit)="submitIngest()" class="mb-6">
        <h2 class="mb-2 text-sm font-medium">Ingest a downloaded subfolder</h2>
        <input
          [(ngModel)]="ingestSubfolder"
          name="ingestSubfolder"
          placeholder="Subfolder (e.g. 110)"
          data-testid="ingest-subfolder-input"
          class="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          [(ngModel)]="ingestDepartment"
          name="ingestDepartment"
          data-testid="ingest-department-select"
          class="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="sporting">Sporting</option>
          <option value="technical">Technical</option>
          <option value="financial">Financial</option>
        </select>
        <button
          type="submit"
          data-testid="ingest-submit"
          class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >Start ingest</button>
        @if (ingestError()) {
          <p class="mt-2 text-sm text-red-600" data-testid="ingest-error">{{ ingestError() }}</p>
        }
      </form>

      <h2 class="mb-2 text-sm font-medium">Active jobs</h2>
      <ul data-testid="active-jobs-list" class="mb-6 text-sm">
        @for (job of activeJobs(); track job.id) {
          <li data-testid="job-row">{{ job.job_type }} — {{ job.target }} — {{ job.status }} ({{ job.id }})</li>
        }
      </ul>

      <h2 class="mb-2 text-sm font-medium">History</h2>
      <ul data-testid="history-jobs-list" class="text-sm">
        @for (job of historyJobs(); track job.id) {
          <li data-testid="job-row">{{ job.job_type }} — {{ job.target }} — {{ job.status }} ({{ job.id }})</li>
        }
      </ul>
    </div>
  `
})
export class JobsComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private pollHandle: ReturnType<typeof setInterval> | null = null;

  private readonly _jobs = signal<JobRecord[]>([]);
  private readonly _loadError = signal(false);
  private readonly _downloadError = signal<string | null>(null);
  private readonly _ingestError = signal<string | null>(null);

  readonly loadError = this._loadError.asReadonly();
  readonly downloadError = this._downloadError.asReadonly();
  readonly ingestError = this._ingestError.asReadonly();

  readonly activeJobs = computed(() =>
    this._jobs().filter((j) => j.status === 'queued' || j.status === 'running')
  );
  readonly historyJobs = computed(() =>
    this._jobs().filter((j) => j.status === 'succeeded' || j.status === 'failed')
  );

  categoryId = '';
  ingestSubfolder = '';
  ingestDepartment = 'sporting';

  ngOnInit(): void {
    this.load();
    this.pollHandle = setInterval(() => {
      if (this.activeJobs().length > 0) {
        this.load();
      }
    }, POLL_INTERVAL_MS);
  }

  ngOnDestroy(): void {
    if (this.pollHandle !== null) {
      clearInterval(this.pollHandle);
    }
  }

  private load(): void {
    this.http.get<JobRecord[]>(JOBS_API_BASE).subscribe({
      next: (jobs) => {
        this._jobs.set(jobs);
        this._loadError.set(false);
      },
      error: () => this._loadError.set(true)
    });
  }

  submitDownload(): void {
    this._downloadError.set(null);
    this.http.post<JobRecord>(`${JOBS_API_BASE}/download`, { category_id: this.categoryId }).subscribe({
      next: (job) => this._jobs.update((jobs) => [job, ...jobs]),
      error: () => this._downloadError.set('Could not start the download job.')
    });
  }

  submitIngest(): void {
    this._ingestError.set(null);
    this.http
      .post<JobRecord>(`${JOBS_API_BASE}/ingest`, {
        subfolder: this.ingestSubfolder,
        department: this.ingestDepartment
      })
      .subscribe({
        next: (job) => this._jobs.update((jobs) => [job, ...jobs]),
        error: () => this._ingestError.set('Could not start the ingest job.')
      });
  }
}
