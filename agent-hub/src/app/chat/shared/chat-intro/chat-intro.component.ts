import { ChangeDetectionStrategy, Component, computed, inject, output } from '@angular/core';
import { PREDEFINED_MESSAGES } from './predefined-msgs';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'acb-chat-intro',
  imports: [],
  templateUrl: './chat-intro.component.html',
  styleUrl: './chat-intro.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatIntroComponent {
  private _auth = inject(AuthService);

  message = output<string>();

  predefinedMessages = PREDEFINED_MESSAGES;

  // Get user's first name for personalized greeting
  userFirstName = computed(() => {
    const user = this._auth.user();
    if (!user) return 'there';

    // Try to get first name from full_name, otherwise use username
    if (user.full_name) {
      return user.full_name.split(' ')[0];
    }
    return user.username;
  });
}
