# Error analysis: configs/final.yaml on train

Counts (k=4): {'success': 73, 'false_abstention': 5, 'wrong_document': 0, 'right_doc_wrong_section': 28, 'partial_span': 34, 'missed_abstention': 1}

## false_abstention (5)

- **Q:** Is there a clause preventing the solicitation of employees in this contract?  (conf=0.25, doc_conf=0.57)
  - truth [25311:25713] (402 chars): During the term of employment and for one (1) year thereafter, the Executive will not directly or indirectly, either themselves or through others, encourage or solicit an
  - top-1 [25420:25913] same_doc=True: either themselves or through others, encourage or solicit any employee of the Company to leave the Company for any reason. This obligation shall not affect any responsibi
  - rank of first overlapping chunk: 1
- **Q:** Is there a clause preventing the solicitation of employees in this contract?  (conf=0.25, doc_conf=0.58)
  - truth [21064:21193] (129 chars): Further, during the Non-Competition Period, Rubicon shall not solicit any employee of ISA or any employee of any ISA Client.
  - top-1 [21016:21513] same_doc=True: or funding to any such ISA Competing Business. Further, during the Non-Competition Period, Rubicon shall not solicit any employee of ISA or any employee of any ISA Client
  - rank of first overlapping chunk: 1
- **Q:** Is there uncapped liability under this contract?  (conf=0.26, doc_conf=0.54)
  - truth [39668:40153] (485 chars): NO PARTY SHALL BE LIABLE FOR CONSEQUENTIAL, INCIDENTAL, PUNITIVE, EXEMPLARY OR INDIRECT DAMAGES, LOST PROFITS OR OTHER BUSINESS INTERRUPTION DAMAGES, BY STATUTE, IN TORT 
  - top-1 [38023:38523] same_doc=True: pect to the Transportation System and Transporter's other facilities, including without limitation, Transporter's Gas gathering system, processing plants and Gas liquids 
  - rank of first overlapping chunk: 2
- **Q:** What happens in the event of a change of control of one of the parties in this contract?  (conf=0.25, doc_conf=0.69)
  - truth [1515:2043] (528 chars): The term of this Agreement shall be effective as of the date first stated above and shall continue for a term of three (3) years, unless terminated earlier in accordance 
  - top-1 [12727:13227] same_doc=True: d) of either PrimeCall or DeltaThree, then the non-bankrupt party may, by written notice thereof to the party in Bankruptcy, terminate this Agreement as of a date specifi
  - rank of first overlapping chunk: 3
- **Q:** Is there a most favored nation clause in this contract?  (conf=0.19, doc_conf=0.49)
  - truth [28071:28291] (220 chars): The grant of licenses to any third parties shall be the prerogative of the Board provided that no such license shall be granted at terms more favorable to the third party
  - top-1 [27746:28242] same_doc=True: ss or product (or the production thereof) for such application to each of the Parties on reasonable commercial terms (including, without limitation, the possible payment 
  - rank of first overlapping chunk: 1

## wrong_document (0)


## right_doc_wrong_section (28)

- **Q:** Are there any exceptions to competitive restrictions in this contract?  (conf=0.35, doc_conf=0.32)
  - truth [33572:34034] (462 chars): save that nothing in this paragraph 13.2 shall prevent you from holding (with the prior written consent of the Company, which shall not be unreasonably delayed or withhel
  - top-1 [38090:38590] same_doc=True: elow only, at any time): (a) in the Restricted Territory, compete with the business of the Company or any Group Company by being directly or indirectly employed or engage
  - rank of first overlapping chunk: None
- **Q:** Does this contract include any right of first refusal, right of first offer, or right of first negotiation?  (conf=0.32, doc_conf=0.32)
  - truth [6235:6531] (296 chars): On or as soon as practicable following the Effective Date, it is intended that you will be granted an option under the Option Plan to acquire 107,417 ordinary shares in t
  - top-1 [32119:32618] same_doc=True: and potential clients or customers of the Company, including customer lists, client 10 lists, names, addresses (including email), telephone, facsimile or other contact nu
  - rank of first overlapping chunk: None
- **Q:** How is intellectual property ownership assigned in this contract?  (conf=0.39, doc_conf=0.32)
  - truth [44840:45359] (519 chars): To the extent that such IPRs do not vest automatically in the Company by operation of law, you hereby assign and agree to assign to the Company all of your right, title a
  - top-1 [48391:48887] same_doc=True: Patents Act 1977 (as amended from time to time). 16 LITIGATION ASSISTANCE During the term of your employment and at all times thereafter subject always to your obligation
  - rank of first overlapping chunk: 8
- **Q:** Can this contract be terminated for convenience, and under what conditions?  (conf=0.30, doc_conf=0.57)
  - truth [18678:18997] (319 chars): The Company may, in its sole and absolute discretion, terminate the Executive's employment under this Agreement at any time and with immediate effect by notifying the Exe
  - top-1 [22246:22743] same_doc=True: e the same conditions that apply to Garden Leave. 19. Garden Leave 19.1 Following service of notice to terminate the employment by either party, or if the Executive purpo
  - rank of first overlapping chunk: 8
- **Q:** Is there a covenant not to sue included in this contract?  (conf=0.40, doc_conf=0.57)
  - truth [27816:28397] (581 chars): If the Executive's employment is terminated at any time by reason of any reconstruction or amalgamation of any Group Company, whether by winding up or otherwise, and the 
  - top-1 [31755:32251] same_doc=True: Act 1999 shall only apply to this Agreement in relation to any Group Company. No person other than the parties to this Agreement and any Group Company shall have any righ
  - rank of first overlapping chunk: 13
- **Q:** What is the expiration date of this contract?  (conf=0.46, doc_conf=0.42)
  - truth [33237:33842] (605 chars): Unless terminated earlier in accordance with the specific terms of this Agreement, the term of this Agreement will begin on the Launch Date and will not end until Excite 
  - top-1 [34599:35097] same_doc=True: d prior to the termination or expiration of this Agreement will be payable in full within thirty (30) days thereof. d) The provisions of Section 12 (Confidentiality and U
  - rank of first overlapping chunk: 6
- **Q:** Are there any exceptions to competitive restrictions in this contract?  (conf=0.35, doc_conf=0.58)
  - truth [23556:23770] (214 chars): In the event that ISA wishes to carry out any software development work of any nature during the Non-Competition Period, it will notify Rubicon of the same and allow Rubi
  - top-1 [21016:21513] same_doc=True: or funding to any such ISA Competing Business. Further, during the Non-Competition Period, Rubicon shall not solicit any employee of ISA or any employee of any ISA Client
  - rank of first overlapping chunk: 9

## partial_span (34)

- **Q:** What is the governing law for this contract?  (conf=0.46, doc_conf=0.4)
  - truth [16867:17117] (250 chars): This Agreement and its application and interpretation will be governed exclusively by its terms and the laws of the State of Nevada (USA), and excluding any conflicts of 
  - top-1 [16572:17072] same_doc=True: attorney fees) to the prevailing Party or a portion of such costs as determined by the arbitrator. An award of the arbitrator shall be final and binding on the Parties an
  - rank of first overlapping chunk: 1
- **Q:** Is there a cap on liability under this contract?  (conf=0.38, doc_conf=0.4)
  - truth [11380:11583] (203 chars): GINARES agrees that the sole and exclusive remedy for money damages related to this Agreement and the transactions contemplated hereby shall be the rights to indemnificat
  - top-1 [11429:11921] same_doc=True: y for money damages related to this Agreement and the transactions contemplated hereby shall be the rights to indemnification set forth in this Section 9. 10. HPIL ET's I
  - rank of first overlapping chunk: 1
- **Q:** How is intellectual property ownership assigned in this contract?  (conf=0.39, doc_conf=0.57)
  - truth [16945:17247] (302 chars): To the extent that the Company IP does not vest automatically in the Company the Executive hereby assigns all right, title and interest in the Company IP to the Company w
  - top-1 [2383:2881] same_doc=True: pany in any jurisdiction from time to time; "Intellectual Property Rights" means patents, rights to Inventions, copyright and related rights, trademarks, trade names and 
  - rank of first overlapping chunk: 2
- **Q:** What is the expiration date of this contract?  (conf=0.46, doc_conf=0.58)
  - truth [18727:19214] (487 chars): Unless terminated sooner, the term of this Agreement shall begin on the Effective Date and continue for three (3) years thereafter (the "Initial Term") and shall automati
  - top-1 [18634:19127] same_doc=True: dification and rights to source code. 6. TERM AND TERMINATION; WITHDRAWAL. 6.1 Term. Unless terminated sooner, the term of this Agreement shall begin on the Effective Dat
  - rank of first overlapping chunk: 1
- **Q:** Does this contract include an exclusivity agreement?  (conf=0.47, doc_conf=0.58)
  - truth [5690:6079] (389 chars): Rubicon hereby grants to ISA during the Term (as defined below) and subject to the exclusions described in 2.4 below an exclusive, non-transferable license in the United 
  - top-1 [6355:6850] same_doc=True: umentation. This license is granted to ISA for the marketing, sale and distribution of the Rubicon Offerings and the Documentation to End Users for their internal use onl
  - rank of first overlapping chunk: 3
- **Q:** What licenses are granted under this contract?  (conf=0.48, doc_conf=0.58)
  - truth [5690:6080] (390 chars): Rubicon hereby grants to ISA during the Term (as defined below) and subject to the exclusions described in 2.4 below an exclusive, non-transferable license in the United 
  - top-1 [6355:6850] same_doc=True: umentation. This license is granted to ISA for the marketing, sale and distribution of the Rubicon Offerings and the Documentation to End Users for their internal use onl
  - rank of first overlapping chunk: 4
- **Q:** Are the licenses granted under this contract non-transferable?  (conf=0.43, doc_conf=0.58)
  - truth [5690:6080] (390 chars): Rubicon hereby grants to ISA during the Term (as defined below) and subject to the exclusions described in 2.4 below an exclusive, non-transferable license in the United 
  - top-1 [6355:6850] same_doc=True: umentation. This license is granted to ISA for the marketing, sale and distribution of the Rubicon Offerings and the Documentation to End Users for their internal use onl
  - rank of first overlapping chunk: 2

## missed_abstention (1)

- **Q:** What happens to the parties' social media accounts after termination?  (conf=0.31, doc_conf=0.66)
  - kind=in_corpus_no_clause
