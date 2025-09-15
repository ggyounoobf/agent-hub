import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
    MODAL_DATA,
    ModalContentComponent,
    ModalController
} from '@ngx-templates/shared/modal';

import { AccessRequest } from '../../../../model';

export interface RequestSubmittedModalData {
    request: AccessRequest;
}

@Component({
    selector: 'acb-request-submitted-modal',
    standalone: true,
    imports: [
        CommonModule,
        ModalContentComponent
    ],
    templateUrl: './request-submitted-modal.component.html',
    styleUrl: './request-submitted-modal.component.scss',
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequestSubmittedModalComponent {
    data = inject<RequestSubmittedModalData>(MODAL_DATA);
    ctrl = inject(ModalController);

    onOk() {
        this.ctrl.close();
    }
}
