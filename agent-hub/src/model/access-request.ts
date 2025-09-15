export interface AccessRequest {
  id: string;
  userId: string;
  userName: string;
  toolName: string;
  toolId: string;
  accessLevel: 'Basic' | 'Advanced' | 'Admin';
  justification: string;
  status: 'Pending' | 'Approved' | 'Denied' | 'Under Review';
  requestedAt: string;
  updatedAt: string;
  duration: 'Temporary' | 'Permanent';
  reason?: string;
  reviewedBy?: string;
  reviewedAt?: string;
  category: string;
  description: string;
}

export interface AccessRequestForm {
  toolName: string;
  toolId: string;
  accessLevel: 'Basic' | 'Advanced' | 'Admin';
  justification: string;
  duration: 'Temporary' | 'Permanent';
  reason?: string;
  category: string;
  description: string;
}