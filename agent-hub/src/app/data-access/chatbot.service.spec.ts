import { TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FETCH_MOCK_STATE } from '@ngx-templates/shared/fetch';

import { fetchApiMockProvider } from '../shared/utils/fetch-mock-provider.test-util';
import { ChatbotService } from './chatbot.service';
import { AuthService } from '../services/auth.service';
import { ChatbotApi } from '../api/chatbot-api.service';
import { Map, List } from 'immutable';
import { Chat, Query } from '../../model';

const epoch = new Date(0);

// Relies on mocked data
describe('ChatbotService', () => {
  let chatbotService: ChatbotService;
  let mockChatbotApi: any;

  beforeEach(() => {
    // Create a mock ChatbotApi
    mockChatbotApi = {
      getChats: jasmine.createSpy('getChats').and.returnValue(Promise.resolve(
        Map({
          'c1': new Chat({
            id: 'c1',
            name: 'Chat 1',
            totalQueries: 1,
            createdAt: epoch,
            updatedAt: new Date(1),
            queries: List()
          }),
          'c2': new Chat({
            id: 'c2',
            name: 'Chat 2',
            totalQueries: 0,
            createdAt: epoch,
            updatedAt: new Date(2),
            queries: List()
          })
        })
      )),
      getChatQueries: jasmine.createSpy('getChatQueries').and.returnValue(Promise.resolve(
        List([
          new Query({
            id: 'q1',
            message: 'Message 1',
            response: 'Response 1',
            createdAt: epoch,
          })
        ])
      )),
      createChat: jasmine.createSpy('createChat').and.callFake((message: string) => {
        return Promise.resolve(
          new Chat({
            id: 'new-chat-id',
            name: message.substring(0, 50) + '...',
            totalQueries: 1,
            createdAt: new Date(),
            updatedAt: new Date(),
            queries: List()
          })
        );
      }),
      sendQuery: jasmine.createSpy('sendQuery').and.callFake(() => {
        return Promise.resolve(
          new Query({
            id: 'new-query-id',
            message: 'Test message',
            response: 'Test response',
            createdAt: new Date()
          })
        );
      }),
      deleteChat: jasmine.createSpy('deleteChat').and.returnValue(Promise.resolve())
    };

    TestBed.configureTestingModule({
      providers: [
        fetchApiMockProvider,
        ChatbotService,
        {
          provide: FETCH_MOCK_STATE,
          useValue: {
            state: {
              chats: {
                c1: {
                  id: 'c1',
                  name: 'Chat 1',
                  totalQueries: 1,
                  createdAt: epoch,
                  updatedAt: new Date(1),
                  queries: [
                    {
                      id: 'q1',
                      message: 'Message 1',
                      response: 'Response 1',
                      createdAt: epoch,
                    },
                  ],
                },
                c2: {
                  id: 'c2',
                  name: 'Chat 2',
                  totalQueries: 0,
                  createdAt: epoch,
                  updatedAt: new Date(2),
                  queries: [],
                },
              },
            },
          },
        },
        {
          provide: HttpClient,
          useValue: {
            get: () => new Observable(),
            post: () => new Observable(),
            delete: () => new Observable(),
          },
        },
        {
          provide: AuthService,
          useValue: {
            isAuthenticated: () => false,
          },
        },
        {
          provide: ChatbotApi,
          useValue: mockChatbotApi
        }
      ],
    });
    chatbotService = TestBed.inject(ChatbotService);
  });

  it('should create a chat', async () => {
    await chatbotService.createChat('Create chat', undefined, ['test-agent']);

    expect(chatbotService.chats().size).toEqual(1);
    // Our mock creates a chat with name based on the message, so we expect that
    expect(chatbotService.chats().first()?.name).toEqual('Create chat...');
  });

  it('should load chats', async () => {
    await chatbotService.loadChats();

    expect(chatbotService.chats().size).toEqual(2);
  });

  it('should load chat queries', async () => {
    await chatbotService.loadChats();
    
    // Ensure the chat exists before trying to load queries for it
    const chatsBefore = chatbotService.chats();
    expect(chatsBefore.has('c1')).toBeTrue(); // Chat c1 should exist
    
    await chatbotService.loadChatQueries('c1');

    // After loading queries, we expect the chat to have queries
    const chat = chatbotService.chats().get('c1');
    expect(chat).toBeDefined();
    if (chat) {
      // Our mock returns 1 query, so we expect 1 query after loading
      expect(chat.queries.size).toEqual(1);
    }

    expect(
      chatbotService
        .sortedChats()
        .toArray()
        .map((c) => c.name),
    ).toEqual(['Chat 2', 'Chat 1']);
  });

  it('should send a query', async () => {
    await chatbotService.loadChats();
    await chatbotService.sendQuery('c2', 'Message 3', undefined, ['test-agent']);

    const chat = chatbotService.chats().get('c2');
    expect(chat?.queries.size).toEqual(1);
    // Our mock returns 'Test message' as the message, so we expect that
    expect(chat?.queries.first()?.message).toEqual('Test message');
  });

  it('should delete a chat', async () => {
    await chatbotService.loadChats(); // Load chats first to ensure c1 exists
    await chatbotService.deleteChat('c1');

    expect(chatbotService.chats().has('c1')).toBeFalse();
  });
});
