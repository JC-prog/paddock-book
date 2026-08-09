import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { JobRecord, JobsComponent } from './jobs.component';

describe('JobsComponent', () => {
  let httpMock: HttpTestingController;

  function setup() {
    TestBed.configureTestingModule({
      imports: [JobsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    httpMock = TestBed.inject(HttpTestingController);

    const fixture = TestBed.createComponent(JobsComponent);
    return fixture;
  }

  afterEach(() => {
    httpMock.verify();
  });

  function text(fixture: ReturnType<typeof setup>): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  function job(overrides: Partial<JobRecord> = {}): JobRecord {
    return {
      id: 'job-1',
      job_type: 'download',
      target: '110',
      status: 'queued',
      params: { category_id: '110' },
      result: null,
      error: null,
      triggered_by_email: 'admin@team.example',
      created_at: '2026-08-09T10:00:00Z',
      started_at: null,
      finished_at: null,
      ...overrides
    };
  }

  it('loads and displays jobs split into active and history sections', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock.expectOne('http://localhost:8000/v1/admin/jobs').flush([
      job({ id: 'active-1', status: 'running' }),
      job({ id: 'history-1', status: 'succeeded' })
    ]);
    fixture.detectChanges();

    const active = fixture.nativeElement.querySelector('[data-testid="active-jobs-list"]');
    const history = fixture.nativeElement.querySelector('[data-testid="history-jobs-list"]');
    expect(active.textContent).toContain('active-1');
    expect(history.textContent).toContain('history-1');
    expect(active.textContent).not.toContain('history-1');
    expect(history.textContent).not.toContain('active-1');
  });

  it('shows an error state when the initial load fails', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock
      .expectOne('http://localhost:8000/v1/admin/jobs')
      .flush({ detail: 'error' }, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(text(fixture).toLowerCase()).toContain('could not load');
  });

  it('submitting the download trigger form calls POST and the new job appears in the active section', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne('http://localhost:8000/v1/admin/jobs').flush([]);
    fixture.detectChanges();

    fixture.componentInstance.categoryId = '110';
    fixture.componentInstance.submitDownload();

    const req = httpMock.expectOne('http://localhost:8000/v1/admin/jobs/download');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ category_id: '110' });
    req.flush(job({ id: 'new-download-job', status: 'queued' }));
    fixture.detectChanges();

    const active = fixture.nativeElement.querySelector('[data-testid="active-jobs-list"]');
    expect(active.textContent).toContain('new-download-job');
  });

  it('submitting the ingest trigger form calls POST and the new job appears in the active section', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne('http://localhost:8000/v1/admin/jobs').flush([]);
    fixture.detectChanges();

    fixture.componentInstance.ingestSubfolder = '110';
    fixture.componentInstance.ingestDepartment = 'sporting';
    fixture.componentInstance.submitIngest();

    const req = httpMock.expectOne('http://localhost:8000/v1/admin/jobs/ingest');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ subfolder: '110', department: 'sporting' });
    req.flush(job({ id: 'new-ingest-job', job_type: 'ingest', status: 'queued' }));
    fixture.detectChanges();

    const active = fixture.nativeElement.querySelector('[data-testid="active-jobs-list"]');
    expect(active.textContent).toContain('new-ingest-job');
  });

  it('renders jobs triggered by a different admin than the current session', () => {
    const fixture = setup();
    fixture.detectChanges();

    httpMock.expectOne('http://localhost:8000/v1/admin/jobs').flush([
      job({ id: 'other-admins-job', status: 'running', triggered_by_email: 'someone-else@team.example' }),
      job({ id: 'my-job', status: 'succeeded', triggered_by_email: 'admin@team.example' })
    ]);
    fixture.detectChanges();

    const active = fixture.nativeElement.querySelector('[data-testid="active-jobs-list"]');
    const history = fixture.nativeElement.querySelector('[data-testid="history-jobs-list"]');
    expect(active.textContent).toContain('other-admins-job');
    expect(history.textContent).toContain('my-job');
  });

  it('shows an error when the download trigger fails', () => {
    const fixture = setup();
    fixture.detectChanges();
    httpMock.expectOne('http://localhost:8000/v1/admin/jobs').flush([]);
    fixture.detectChanges();

    fixture.componentInstance.categoryId = '110';
    fixture.componentInstance.submitDownload();

    httpMock
      .expectOne('http://localhost:8000/v1/admin/jobs/download')
      .flush({ detail: 'duplicate' }, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();

    const errorEl = fixture.nativeElement.querySelector('[data-testid="download-error"]');
    expect(errorEl).toBeTruthy();
  });
});
