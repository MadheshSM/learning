import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ViewerAction {
  operation: string;
  params: Record<string, any>;
  description?: string;
}

export interface QueryResponse {
  success: boolean;
  message: string;
  viewer_actions?: ViewerAction[];
  agents_used?: string[];
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatApiService {
  private apiUrl = 'http://localhost:8080'; // Configure this

  constructor(private http: HttpClient) {}

  setApiUrl(url: string): void {
    this.apiUrl = url;
  }

  sendQuery(query: string, modelContext?: { selectedIds?: number[], modelUrn?: string }): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(`${this.apiUrl}/api/query`, {
      query,
      model_context: modelContext
    });
  }

  checkHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/health`);
  }
}
