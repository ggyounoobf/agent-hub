import { List, Map } from 'immutable';
import { Chat, Query } from '../../../model';
import { ApiChat, ApiQuery } from './api-types';

export const mapQuery = (query: any) =>
  new Query({
    id: query.id,
    chatId: query.chat_id,
    message: query.message,
    response: query.response,
    createdAt: new Date(query.created_at),
    filesUploaded: query.files_uploaded || [],
    status: query.status || null,
    errorMessage: query.error_message || null
  });

export const mapQueries = (queries: any[]) => List(queries.map(mapQuery));

export const mapChat = (chat: any) =>
  new Chat({
    id: chat.id,
    name: chat.title || 'Untitled Chat',
    createdAt: new Date(chat.created_at),
    updatedAt: new Date(chat.updated_at),
    totalQueries: chat.total_queries || chat.total || 0,
    queries: mapQueries(chat.queries || chat.items || []),
  });

export const mapChats = (chats: any[]) =>
  Map<string, Chat>(chats.map((c) => [c.id, mapChat(c)]));
