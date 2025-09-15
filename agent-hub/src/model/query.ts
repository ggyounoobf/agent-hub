import { Record } from 'immutable';

export interface FileUploaded {
  id: string;
  name: string;
  uploaded_at: string; // Keep as string to match API response
}

interface QueryConfig {
  id: string;
  chatId?: string;
  message: string;
  response: string;
  createdAt: Date;
  filesUploaded?: FileUploaded[];
  status?: 'completed' | 'failed' | 'processing' | null;
  errorMessage?: string | null;
}

const queryRecord = Record<QueryConfig>({
  id: '',
  chatId: '',
  message: '',
  response: '',
  createdAt: new Date(0),
  filesUploaded: [],
  status: null,
  errorMessage: null,
});

export class Query extends queryRecord {
  constructor(config: Partial<QueryConfig>) {
    super(config);
  }
}
