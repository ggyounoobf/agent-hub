export type ApiFileUploaded = {
  id: string;
  name: string;
  uploaded_at: string;
};

export type ApiQuery = {
  id: string;
  message: string;
  created_at: string;
  response: string;
  files_uploaded?: ApiFileUploaded[];
};

export type ApiChat = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  total_queries: number;
  queries?: ApiQuery[];
};

export type ApiChatPage = {
  id: string;
  queries: ApiQuery[];
};
