import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { ViewerChatComponent } from './viewer-chat.component';
import { ChatApiService } from './chat-api.service';
import { ViewerActionExecutorService } from './viewer-action-executor.service';

@NgModule({
  declarations: [
    ViewerChatComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule
  ],
  exports: [
    ViewerChatComponent
  ],
  providers: [
    ChatApiService,
    ViewerActionExecutorService
  ]
})
export class ViewerChatModule {}
